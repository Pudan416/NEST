"""
Location handling and place discovery handlers.
"""

import asyncio
from aiogram import F
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from app.languages import get_message, get_user_language
from app import logger
from app.generators import (
    deepseek_location_info,
    yandex_speechkit_tts,
    translate_to_english,
    get_http_client,
)
from app.google_maps import (
    get_nearby_places,
    get_detailed_address,
    get_walking_directions_polyline,
)
from app.maps_static import get_static_map_image
from geopy.distance import geodesic
from .state import (
    router,
    user_data,
    active_deepseek_requests,
    user_preferences,
    POI_CATEGORY_MAPPING,
)


@router.message(F.location)
async def handle_location(message: Message, db=None):
    """Handle user's shared location."""
    try:
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        latitude = message.location.latitude
        longitude = message.location.longitude

        # Check if user has any place types selected
        if user_id in user_preferences:
            prefs = user_preferences[user_id]
            if not any(prefs.values()):
                await message.answer(get_message("no_places_selected", lang))
                return

        # Initialize http client
        http_client = await get_http_client()

        # Get user preferences
        selected_poi_types = []
        if user_id in user_preferences:
            prefs = user_preferences[user_id]
            for category, is_selected in prefs.items():
                if is_selected:
                    selected_poi_types.extend(POI_CATEGORY_MAPPING[category])

        if not selected_poi_types:
            selected_poi_types = ["tourist_attraction", "museum"]

        # Show initial status message
        status_message = await message.answer(get_message("scouting", lang))

        tasks = [
            get_detailed_address(latitude, longitude, http_client),
            get_nearby_places(
                latitude,
                longitude,
                radius=1000,
                place_types=selected_poi_types,
                http_client=http_client,
            ),
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
            await status_message.edit_text(get_message("searching_wider", lang))
            wider_search_task = asyncio.create_task(
                get_nearby_places(
                    latitude,
                    longitude,
                    radius=5000,
                    place_types=selected_poi_types,
                    http_client=http_client,
                )
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
            await status_message.edit_text(get_message("searching_farthest", lang))
            try:
                widest_places = await asyncio.wait_for(
                    get_nearby_places(
                        latitude,
                        longitude,
                        radius=10000,
                        place_types=selected_poi_types,
                        http_client=http_client,
                    ),
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
            await status_message.edit_text(get_message("no_places", lang))
            return

        valid_places.sort(key=lambda x: x["distance"])
        closest_places = valid_places[:5] if len(valid_places) >= 5 else valid_places

        # Update status message to indicate we're generating a map
        await status_message.edit_text(get_message("generating_map", lang))

        # Generate the static map for all places
        map_image = await get_static_map_image(
            closest_places, latitude, longitude, http_client
        )

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
            "map_image": map_image,
        }

        # First send the message about found places
        places_count_message = get_message("places_found", lang).format(
            count=len(closest_places)
        )
        await status_message.edit_text(places_count_message)

        # Then send the map image
        if map_image:
            try:
                photo = BufferedInputFile(map_image, filename="map.png")
                map_caption = get_message("map_caption", lang).format(
                    count=len(closest_places)
                )
                await message.answer_photo(photo=photo, caption=map_caption)
            except Exception as map_error:
                logger.error(f"Error sending map image: {map_error}")

        # Show the first place details
        await show_place(message, user_id, 0)

    except Exception as e:
        logger.error(f"Error in location handler: {e}", exc_info=True)
        await message.answer(get_message("try_again", lang))


async def show_place(message, user_id, place_index):
    """Show details of a specific place."""
    try:
        if user_id not in user_data:
            await message.answer(get_message("lost_track", get_user_language(user_id)))
            return

        data = user_data[user_id]
        places = data["places"]
        lang = get_user_language(user_id)

        if place_index < 0 or place_index >= len(places):
            place_index = 0

        # Number emojis for places
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        current_emoji = (
            number_emojis[place_index]
            if place_index < len(number_emojis)
            else str(place_index + 1)
        )

        data["current_index"] = place_index
        place = places[place_index]
        place_lat = place["position"]["lat"]
        place_lng = place["position"]["lng"]

        needs_processing = (
            not "original_title" in place
            or place["address"].get("label") == "Address will be fetched"
            or "title" in place
            and place["title"] == place.get("original_title")
        )

        if needs_processing:
            processing_message = await message.answer(
                get_message("reading_signs", lang)
            )

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
                await processing_message.delete()
            except Exception:
                pass

        # Determine which name to show first based on language
        if lang == "ru":
            primary_name = place.get("original_title", place["title"])
            secondary_name = place["title"]
        else:
            primary_name = place["title"]
            secondary_name = place.get("original_title", place["title"])

        place_address = place["address"]["label"]
        distance_km = place["distance"] / 1000
        place_type = place.get("type", "point of interest")

        google_maps_url = (
            f"https://www.google.com/maps/search/?api=1&query={place_lat},{place_lng}"
        )

        next_text = (
            get_message("next_location", lang)
            if place_index < len(places) - 1
            else get_message("back_to_first", lang)
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_message("tell_more_btn", lang),
                        callback_data=f"more_{place_index}",
                    ),
                    InlineKeyboardButton(
                        text=get_message("show_maps_btn", lang),
                        url=google_maps_url,
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=next_text,
                        callback_data=f"next_{(place_index + 1) % len(places)}",
                    )
                ],
            ]
        )

        # Format the message with number emoji, primary name in bold and secondary name in italic
        message_text = f"{current_emoji} <b>{primary_name}</b>"
        if secondary_name and secondary_name != primary_name:
            message_text += f"\n<i>{secondary_name}</i>"

        message_text += f"\n\n📍 {place_address}\n"
        message_text += f"🚶 {distance_km:.1f} km\n"
        message_text += f"🏷️ {place_type}\n"

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
                    message_text, parse_mode="HTML", reply_markup=keyboard
                )
            except Exception as edit_error:
                logger.error(f"Error editing message: {edit_error}")
                sent_message = await message.answer(
                    message_text, parse_mode="HTML", reply_markup=keyboard
                )
                data["last_message"] = sent_message
        else:
            sent_message = await message.answer(
                message_text, parse_mode="HTML", reply_markup=keyboard
            )
            data["last_message"] = sent_message

    except Exception as e:
        logger.error(f"Error in show_place: {e}", exc_info=True)
        await message.answer(
            get_message("error_showing_place", get_user_language(user_id))
        )


@router.callback_query(F.data.startswith("next_"))
async def handle_next_location(callback: CallbackQuery):
    """Handle showing the next location."""
    try:
        await callback.answer()
        user_id = callback.from_user.id
        _, index = callback.data.split("_")
        index = int(index)
        lang = get_user_language(user_id)

        if user_id not in user_data:
            await callback.message.answer(get_message("lost_track", lang))
            return

        await show_place(callback.message, user_id, index)

    except Exception as e:
        logger.error(f"Error in next location handler: {e}", exc_info=True)
        await callback.message.answer(
            get_message("error_next_place", get_user_language(user_id))
        )


@router.callback_query(F.data.startswith("more_"))
async def handle_tell_more(callback: CallbackQuery):
    """Handle request for more information about a place."""
    request_key = None
    http_client = None
    user_id = callback.from_user.id
    lang = get_user_language(user_id)

    try:
        _, index = callback.data.split("_")
        index = int(index)

        if user_id not in user_data:
            await callback.answer(
                get_message("lost_track_alert", lang), show_alert=True
            )
            return

        request_key = f"{user_id}_{index}"

        if request_key in active_deepseek_requests:
            if active_deepseek_requests[request_key]["active"]:
                await callback.answer(
                    get_message("request_in_progress", lang), show_alert=True
                )
                return

            last_request_time = active_deepseek_requests[request_key]["timestamp"]
            current_time = asyncio.get_event_loop().time()

            if current_time - last_request_time < 300:
                remaining = int(300 - (current_time - last_request_time))
                await callback.answer(
                    get_message("cooldown", lang).format(seconds=remaining),
                    show_alert=True,
                )
                return

        await callback.answer(get_message("gathering_thoughts", lang))

        data = user_data[user_id]
        places = data["places"]
        place = places[index]

        user_lat = data["latitude"]
        user_lng = data["longitude"]
        place_lat = place["position"]["lat"]
        place_lng = place["position"]["lng"]

        active_deepseek_requests[request_key] = {
            "active": True,
            "timestamp": asyncio.get_event_loop().time(),
        }

        http_client = await get_http_client()

        walking_polyline = await get_walking_directions_polyline(
            user_lat, user_lng, place_lat, place_lng, http_client
        )

        route_map_image = None
        if walking_polyline:
            route_map_image = await get_static_map_image(
                places=[place],
                user_lat=user_lat,
                user_lng=user_lng,
                http_client=http_client,
                path_polyline=walking_polyline,
            )

        google_maps_url = (
            f"https://www.google.com/maps/search/?api=1&query={place_lat},{place_lng}"
        )
        next_text = (
            get_message("next_location", lang)
            if index < len(places) - 1
            else get_message("back_to_first", lang)
        )
        new_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_message("show_maps_btn", lang), url=google_maps_url
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=next_text,
                        callback_data=f"next_{(index + 1) % len(places)}",
                    )
                ],
            ]
        )
        try:
            if callback.message:
                await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        except Exception as e:
            logger.error(f"Error updating buttons: {e}")

        if (
            not "title" in place
            or place["title"] == place.get("original_title")
            or place["address"].get("label") == "Address will be fetched"
        ):
            status_msg = await callback.message.answer(
                get_message("checking_details", lang)
            )
            detailed_address, _ = await get_detailed_address(
                place_lat, place_lng, http_client
            )

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

        # Determine which name to show based on language
        if lang == "ru":
            display_name = place.get("original_title", place["title"])
        else:
            display_name = place["title"]

        # Number emojis for places
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        current_emoji = (
            number_emojis[index] if index < len(number_emojis) else str(index + 1)
        )

        if "history" in place and place["history"]:
            history = place["history"]
            history_msg = await callback.message.answer(
                get_message("remembered_place", lang)
            )
        else:
            history_msg = await callback.message.answer(
                get_message("digging_memories", lang)
            )
            history = await deepseek_location_info(
                data["city"],
                data["street"],
                display_name,
                place["address"]["label"],
                place.get("original_title"),
                http_client,
                lang,
            )
            place["history"] = history

        history_message_text = get_message("about_place", lang).format(
            place_name=f"{current_emoji} {display_name}", history=history
        )

        if route_map_image:
            try:
                photo = BufferedInputFile(route_map_image, filename="route_map.png")
                await callback.message.answer_photo(
                    photo=photo, caption=f"🚶 Walking route to {display_name}"
                )
            except Exception as map_error:
                logger.error(f"Error sending route map image: {map_error}")

        await callback.message.answer(history_message_text, parse_mode="HTML")

        try:
            await history_msg.delete()
        except Exception:
            pass

        if not place.get("audio_sent", False):
            audio_bytes = await yandex_speechkit_tts(history, http_client, lang)
            if audio_bytes:
                if len(audio_bytes) > 50 * 1024 * 1024:
                    await callback.message.answer(get_message("audio_too_large", lang))
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
                                logger.error(
                                    f"Failed to send audio after 3 attempts: {e}"
                                )
                                await callback.message.answer(
                                    get_message("voice_tired", lang)
                                )
                            await asyncio.sleep(2)

        active_deepseek_requests[request_key]["active"] = False

    except Exception as e:
        if request_key and request_key in active_deepseek_requests:
            active_deepseek_requests[request_key]["active"] = False

        logger.error(f"Error in tell more handler: {e}", exc_info=True)
        await callback.message.answer(get_message("forgot_to_say", lang))
    finally:
        if http_client:
            await http_client.aclose()


@router.message()
async def handle_unknown(message: Message, db=None):
    """Handle unknown messages."""
    try:
        user_id = message.from_user.id
        lang = get_user_language(user_id)

        if db:
            db.add_or_update_user(
                user_id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
            )

        await message.answer(get_message("need_location", lang))
    except Exception as e:
        logger.error(f"Error in unknown message handler: {e}", exc_info=True)
        await message.answer(get_message("error", get_user_language(user_id)))
