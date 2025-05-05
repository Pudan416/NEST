import os
from aiogram import Router, F, BaseMiddleware
from aiogram.types import Message, BufferedInputFile, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from app.generators import (
    deepseek_location_info,
    yandex_speechkit_tts,
    translate_to_english,
    get_http_client,
)
from app.google_maps import get_nearby_places, get_detailed_address
from app.maps_static import get_static_map_image  # Import the new module
from typing import Dict, Any, Callable, Awaitable
from geopy.distance import geodesic
import asyncio
from app import logger
from app.texts import MESSAGES

router = Router()

# Store user data
user_data = {}
# Store active DeepSeek requests to prevent duplicates
active_deepseek_requests = {}


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        return await handler(event, data)


router.message.middleware(DatabaseMiddleware())


@router.message(CommandStart())
async def handle_start_command(message: Message, db=None):
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name

        logger.info(f"Received '/start' command from user: {user_id}")

        if db:
            db.add_or_update_user(user_id, username, first_name, last_name)


        await message.answer(MESSAGES['start'])
    except Exception as e:
        logger.error(f"Error in '/start' command handler: {e}", exc_info=True)
        await message.answer(MESSAGES['error'])


@router.message(F.location)
async def handle_location(message: Message, db=None):
    try:
        user_id = message.from_user.id
        latitude, longitude = message.location.latitude, message.location.longitude
        logger.info(f"Received location from user {user_id}: {latitude}, {longitude}")

        if db:
            db.add_or_update_user(
                user_id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
            )

        status_message = await message.answer(MESSAGES['scouting'])

        http_client = await get_http_client()

        tasks = [
            get_detailed_address(latitude, longitude, http_client),
            get_nearby_places(latitude, longitude, radius=1000, http_client=http_client),
        ]

        results = await asyncio.gather(*tasks)
        address_result, places = results[0], results[1]

        address, address_data = address_result
        address_parts = address_data.get("address", {})
        street = address.split(",")[0] if "," in address else "Unknown Street"
        city = address_parts.get("city", "Unknown City")

        translation_tasks = [translate_to_english(street), translate_to_english(city)]

        wider_search_task = None
        if len(places) < 5:
            await status_message.edit_text(MESSAGES['searching_wider'])
            wider_search_task = asyncio.create_task(
                get_nearby_places(latitude, longitude, radius=5000, http_client=http_client)
            )

        english_street, english_city = await asyncio.gather(*translation_tasks)

        valid_places = []
        for place in places:
            if "unknown" in place["title"].lower():
                continue

            place["distance"] = geodesic(
                (latitude, longitude),
                (place["position"]["lat"], place["position"]["lng"]),
            ).meters
            valid_places.append(place)

        if wider_search_task:
            done, pending = await asyncio.wait([wider_search_task], timeout=3)

            if done:
                wider_places = wider_search_task.result()
                for place in wider_places:
                    if "unknown" in place["title"].lower():
                        continue
                    if not any(p["id"] == place["id"] for p in valid_places):
                        place["distance"] = geodesic(
                            (latitude, longitude),
                            (place["position"]["lat"], place["position"]["lng"]),
                        ).meters
                        valid_places.append(place)
            else:
                wider_search_task.cancel()
                try:
                    await wider_search_task
                except asyncio.CancelledError:
                    pass

        if len(valid_places) < 2:
            await status_message.edit_text(MESSAGES['searching_farthest'])
            try:
                widest_places = await asyncio.wait_for(
                    get_nearby_places(latitude, longitude, radius=10000, http_client=http_client),
                    timeout=4,
                )

                for place in widest_places:
                    if "unknown" in place["title"].lower():
                        continue
                    if not any(p["id"] == place["id"] for p in valid_places):
                        place["distance"] = geodesic(
                            (latitude, longitude),
                            (place["position"]["lat"], place["position"]["lng"]),
                        ).meters
                        valid_places.append(place)
            except asyncio.TimeoutError:
                pass

        if not valid_places:
            await status_message.edit_text(MESSAGES['no_places'])
            return

        valid_places.sort(key=lambda x: x["distance"])
        closest_places = valid_places[:5] if len(valid_places) >= 5 else valid_places

        # Update status message to indicate we're generating a map
        await status_message.edit_text(MESSAGES['generating_map'])
        
        # Generate the static map for all places
        map_image = await get_static_map_image(closest_places, latitude, longitude, http_client)

        # Store the user data
        user_data[user_id] = {
            "places": closest_places,
            "current_index": 0,
            "latitude": latitude,
            "longitude": longitude,
            "street": english_street,
            "city": english_city,
            "db": db,
            "last_message": None,
            "map_image": map_image  # Store the map image in user data
        }

        # First send the message about found places
        places_count_message = MESSAGES['places_found'].format(count=len(closest_places))
        await status_message.edit_text(places_count_message)
        
        # Then send the map image
        if map_image:
            try:
                photo = BufferedInputFile(map_image, filename="map.png")
                map_caption = MESSAGES['map_caption'].format(count=len(closest_places))
                await message.answer_photo(photo=photo, caption=map_caption)
            except Exception as map_error:
                logger.error(f"Error sending map image: {map_error}")
                # If we can't send the map, still continue with text

        # Show the first place details
        await show_place(message, user_id, 0)

    except Exception as e:
        logger.error(f"Error in location handler: {e}", exc_info=True)
        await message.answer(MESSAGES['try_again'])


async def show_place(message, user_id, place_index):
    try:
        if user_id not in user_data:
            await message.answer(MESSAGES['lost_track'])
            return

        data = user_data[user_id]
        places = data["places"]

        if place_index < 0 or place_index >= len(places):
            place_index = 0

        data["current_index"] = place_index
        place = places[place_index]
        place_name = place.get("title", "Unknown Place")
        place_lat = place["position"]["lat"]
        place_lng = place["position"]["lng"]

        needs_processing = (
            not "original_title" in place
            or place["address"].get("label") == "Address will be fetched"
            or "title" in place and place["title"] == place.get("original_title")
        )

        if needs_processing:
            processing_message = await message.answer(MESSAGES['reading_signs'])

            detailed_address, _ = await get_detailed_address(place_lat, place_lng)

            if not "original_title" in place:
                place["original_title"] = place["title"]
            place["original_address"] = detailed_address

            translation_tasks = [
                translate_to_english(place["original_title"]),
                translate_to_english(detailed_address),
            ]

            english_name, english_address = await asyncio.gather(*translation_tasks)

            place["title"] = english_name
            place["address"] = {"label": english_address}
            place_name = english_name

            try:
                await processing_message.delete()
            except Exception:
                pass

        place_name = place["title"]
        original_name = place.get("original_title", place_name)
        place_address = place["address"]["label"]
        distance_km = place["distance"] / 1000
        place_type = place.get("type", "point of interest")
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={place_lat},{place_lng}"

        next_text = MESSAGES['next_location'] if place_index < len(places) - 1 else MESSAGES['back_to_first']
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=MESSAGES['tell_more_btn'], callback_data=f"more_{place_index}"
                    ),
                    InlineKeyboardButton(
                        text=MESSAGES['show_maps_btn'], url=google_maps_url
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=next_text,
                        callback_data=f"next_{(place_index + 1) % len(places)}",
                    )
                ]
            ]
        )

        if data.get("db") and not place.get("logged", False):
            db = data["db"]
            db.log_search(
                user_id, place_name, place_type, place_lat, place_lng, data["city"]
            )
            place["logged"] = True

        # Include the marker number in the message title
        message_text = f"<b>#{place_index + 1}: {place_name.upper()}</b> ({place_index + 1}/{len(places)})"

        if original_name != place_name:
            message_text += f" (<i>{original_name}</i>)"

        message_text += f"\n📍 <b>Address:</b> <code>{place_address}</code>\n"
        message_text += f"🚶 <b>Distance:</b> {distance_km:.1f} km\n"
        message_text += f"🏷️ <b>Type:</b> {place_type}"

        place_url = place.get("contacts", [])
        if place_url:
            place_url = place_url[0].get("www", "url_not_found")
            if isinstance(place_url, list) and place_url:
                place_url = place_url[0].get("value", "url_not_found")

            if place_url != "url_not_found":
                message_text += f"\n🌐 <b>Website:</b> {place_url}"

        if "last_message" in data and data["last_message"]:
            try:
                await data["last_message"].edit_text(
                    message_text, 
                    parse_mode="HTML", 
                    reply_markup=keyboard
                )
            except Exception as edit_error:
                logger.error(f"Error editing message: {edit_error}")
                sent_message = await message.answer(
                    message_text, 
                    parse_mode="HTML", 
                    reply_markup=keyboard
                )
                data["last_message"] = sent_message
        else:
            sent_message = await message.answer(
                message_text, 
                parse_mode="HTML", 
                reply_markup=keyboard
            )
            data["last_message"] = sent_message

    except Exception as e:
        logger.error(f"Error in show_place: {e}", exc_info=True)
        await message.answer(MESSAGES['error_showing_place'])


@router.callback_query(F.data.startswith("next_"))
async def handle_next_location(callback: CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        _, index = callback.data.split("_")
        index = int(index)

        if user_id not in user_data:
            await callback.message.answer(MESSAGES['lost_track'])
            return

        await show_place(callback.message, user_id, index)

    except Exception as e:
        logger.error(f"Error in next location handler: {e}", exc_info=True)
        await callback.message.answer(MESSAGES['error_next_place'])


@router.callback_query(F.data.startswith("more_"))
async def handle_tell_more(callback: CallbackQuery):
    request_key = None
    place_name = None
    history = None

    try:
        user_id = callback.from_user.id
        _, index = callback.data.split("_")
        index = int(index)

        if user_id not in user_data:
            await callback.answer(MESSAGES['lost_track_alert'], show_alert=True)
            return

        request_key = f"{user_id}_{index}"

        if request_key in active_deepseek_requests:
            if active_deepseek_requests[request_key]["active"]:
                await callback.answer(MESSAGES['request_in_progress'], show_alert=True)
                return

            last_request_time = active_deepseek_requests[request_key]["timestamp"]
            current_time = asyncio.get_event_loop().time()

            if current_time - last_request_time < 300:
                remaining = int(300 - (current_time - last_request_time))
                await callback.answer(
                    MESSAGES['cooldown'].format(seconds=remaining), show_alert=True
                )
                return

        await callback.answer(MESSAGES['gathering_thoughts'])

        data = user_data[user_id]
        place = data["places"][index]

        active_deepseek_requests[request_key] = {
            "active": True,
            "timestamp": asyncio.get_event_loop().time(),
        }

        current_message = callback.message
        new_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=MESSAGES['tell_more_btn'], callback_data=f"more_{index}"
                    ),
                ]
            ]
        )
        try:
            await current_message.edit_reply_markup(reply_markup=new_keyboard)
        except Exception as e:
            logger.error(f"Error removing 'Next location' button: {e}")

        if (
            not "title" in place
            or place["title"] == place.get("original_title")
            or place["address"].get("label") == "Address will be fetched"
        ):
            status_msg = await callback.message.answer(MESSAGES['checking_details'])
            place_lat = place["position"]["lat"]
            place_lng = place["position"]["lng"]
            detailed_address, _ = await get_detailed_address(place_lat, place_lng)

            if not "original_title" in place:
                place["original_title"] = place["title"]
            place["original_address"] = detailed_address

            translation_tasks = [
                translate_to_english(place["original_title"]),
                translate_to_english(detailed_address),
            ]

            english_name, english_address = await asyncio.gather(*translation_tasks)
            place["title"] = english_name
            place["address"] = {"label": english_address}

            try:
                await status_msg.delete()
            except Exception:
                pass

        place_name = place["title"]
        original_name = place.get("original_title", place_name)
        place_address = place["address"]["label"]

        if "history" in place and place["history"]:
            history = place["history"]
            history_msg = await callback.message.answer(MESSAGES['remembered_place'])
        else:
            history_msg = await callback.message.answer(MESSAGES['digging_memories'])
            history = await deepseek_location_info(
                data["city"], data["street"], place_name, place_address, original_name
            )
            place["history"] = history

        history_message = MESSAGES['about_place'].format(place_name=place_name, history=history)
        await callback.message.answer(history_message, parse_mode="HTML")

        try:
            await history_msg.delete()
        except Exception:
            pass

        if not "audio_sent" in place or not place["audio_sent"]:
            audio_bytes = await yandex_speechkit_tts(history)

            if audio_bytes:
                if len(audio_bytes) > 50 * 1024 * 1024:
                    await callback.message.answer(MESSAGES['audio_too_large'])
                else:
                    for attempt in range(3):
                        try:
                            audio_file = BufferedInputFile(
                                audio_bytes, filename="voice_message.mp3"
                            )
                            await callback.message.answer_voice(voice=audio_file)
                            place["audio_sent"] = True
                            break
                        except Exception as e:
                            if attempt == 2:
                                logger.error(f"Failed to send audio after 3 attempts: {e}")
                                await callback.message.answer(MESSAGES['voice_tired'])
                            await asyncio.sleep(2)

        active_deepseek_requests[request_key]["active"] = False

    except Exception as e:
        if request_key:
            active_deepseek_requests[request_key] = {
                "active": False,
                "timestamp": asyncio.get_event_loop().time(),
            }

        logger.error(f"Error in tell more handler: {e}", exc_info=True)
        await callback.message.answer(MESSAGES['forgot_to_say'])

        if place_name and history:
            history_message = MESSAGES['about_place'].format(place_name=place_name, history=history)
            await callback.message.answer(history_message, parse_mode="HTML")

            audio_bytes = await yandex_speechkit_tts(history)

            if audio_bytes:
                if len(audio_bytes) > 50 * 1024 * 1024:
                    await callback.message.answer(MESSAGES['audio_too_large'])
                else:
                    for attempt in range(3):
                        try:
                            audio_file = BufferedInputFile(
                                audio_bytes, filename="voice_message.mp3"
                            )
                            await callback.message.answer_voice(voice=audio_file)
                            break
                        except Exception as e:
                            if attempt == 2:
                                logger.error(f"Failed to send audio after 3 attempts: {e}")
                                await callback.message.answer(MESSAGES['voice_tired'])
                            await asyncio.sleep(2)


@router.message()
async def handle_unknown(message: Message, db=None):
    try:
        user_id = message.from_user.id

        if db:
            db.add_or_update_user(
                user_id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
            )

        await message.answer(MESSAGES['need_location'])
    except Exception as e:
        logger.error(f"Error in unknown message handler: {e}", exc_info=True)
        await message.answer(MESSAGES['error'])