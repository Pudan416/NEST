import os 
from aiogram import Router, F, BaseMiddleware
from aiogram.types import Message, BufferedInputFile, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from app.generators import (
    deepseek_location_info,
    yandex_speechkit_tts,
    test_deepseek_connection,
    translate_to_english,
    get_http_client,
)
from app.google_maps import get_nearby_places, get_detailed_address, get_place_details
from typing import Dict, Any, Callable, Awaitable
import httpx
from geopy.distance import geodesic
import asyncio
from app import logger

router = Router()

# Store user data
user_data = {}

# Store active DeepSeek requests to prevent duplicates
active_deepseek_requests = {}


# Database middleware
class DatabaseMiddleware(BaseMiddleware):
    """Middleware for injecting database into handler data."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # The database is expected to be passed from dispatcher to router
        # We don't modify data here, just pass it through
        return await handler(event, data)


# Apply middleware to router
router.message.middleware(DatabaseMiddleware())


@router.message(CommandStart())
async def handle_start_command(message: Message, db=None):
    """Handle the /start command."""
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name

        logger.info(f"Received '/start' command from user: {user_id}")

        # Update user info in database if available
        if db:
            db.add_or_update_user(user_id, username, first_name, last_name)

        await message.answer(
            "🐦 Coo-coo-COOOO! Nesty is here! \n\n"
            "Welcome to NEST - Navigate, Explore, See, Travel!\n"
            "I've fluttered over every inch of this city. You might've spotted me perched overhead! \n\n"
            "📍 Drop your location and I'll find the best nearby spots worth your attention!\n\n"
            "Let's spread our wings and explore together!"
        )
    except Exception as e:
        logger.error(f"Error in '/start' command handler: {e}", exc_info=True)
        await message.answer("An error occurred. Please try again later.")


@router.message(F.location)
async def handle_location(message: Message, db=None):
    """Handle location messages and provide information about nearby tourist attractions."""
    try:
        user_id = message.from_user.id
        latitude, longitude = message.location.latitude, message.location.longitude
        logger.info(f"Received location from user {user_id}: {latitude}, {longitude}")

        # Update user's last active timestamp
        if db:
            db.add_or_update_user(
                user_id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
            )

        # Send initial status message and store the message object to edit it later
        status_message = await message.answer("🐦 Taking off to scout the area!")

        # Get user's current location details and start Google Maps search in parallel
        from app.google_maps import get_detailed_address, get_nearby_places

        # Initialize HTTP client for reuse
        http_client = await get_http_client()

        # Execute both tasks concurrently
        tasks = [
            get_detailed_address(latitude, longitude, http_client),
            # Start with a small radius for faster initial results
            get_nearby_places(
                latitude, longitude, radius=1000, http_client=http_client
            ),
        ]

        results = await asyncio.gather(*tasks)
        address_result, places = results[0], results[1]

        address, address_data = address_result
        address_parts = address_data.get("address", {})
        street = address.split(",")[0] if "," in address else "Unknown Street"
        city = address_parts.get("city", "Unknown City")

        # Start translating while potentially doing additional searches
        translation_tasks = [translate_to_english(street), translate_to_english(city)]

        # If we didn't find enough places with the small radius, start a wider search
        # but don't wait for it to complete before proceeding with what we have
        wider_search_task = None
        if len(places) < 5:
            await status_message.edit_text(
                "🐦 Found a few spots nearby, but searching wider for more options..."
            )
            wider_search_task = asyncio.create_task(
                get_nearby_places(
                    latitude, longitude, radius=5000, http_client=http_client
                )
            )

        # Get translation results
        english_street, english_city = await asyncio.gather(*translation_tasks)

        logger.debug(f"Current location: {street}, {city}")
        logger.debug(f"Translated location: {english_street}, {english_city}")

        # Initial filtering of places we've found so far
        valid_places = []
        for place in places:
            if "unknown" in place["title"].lower():
                continue

            place["distance"] = geodesic(
                (latitude, longitude),
                (place["position"]["lat"], place["position"]["lng"]),
            ).meters
            valid_places.append(place)

        # If we started a wider search, check if it's complete
        if wider_search_task:
            # Wait for up to 3 seconds to get more results
            done, pending = await asyncio.wait([wider_search_task], timeout=3)

            if done:
                # Wider search completed in time, process the results
                wider_places = wider_search_task.result()

                # Process wider search results
                for place in wider_places:
                    if "unknown" in place["title"].lower():
                        continue

                    # Check if this place is already in our list (by ID)
                    if not any(p["id"] == place["id"] for p in valid_places):
                        place["distance"] = geodesic(
                            (latitude, longitude),
                            (place["position"]["lat"], place["position"]["lng"]),
                        ).meters
                        valid_places.append(place)
            else:
                # Wider search is taking too long, cancel it
                wider_search_task.cancel()
                try:
                    await wider_search_task
                except asyncio.CancelledError:
                    logger.debug("Cancelled wider search to maintain responsiveness")

        # If we still don't have enough places, try one more wider search
        # but only if we've found very few places so far
        if len(valid_places) < 2:
            await status_message.edit_text(
                "🐦 Just a few more seconds while I search farther away..."
            )
            try:
                widest_places = await asyncio.wait_for(
                    get_nearby_places(
                        latitude, longitude, radius=10000, http_client=http_client
                    ),
                    timeout=4,  # strict timeout
                )

                # Process widest search results
                for place in widest_places:
                    if "unknown" in place["title"].lower():
                        continue

                    # Check if this place is already in our list (by ID)
                    if not any(p["id"] == place["id"] for p in valid_places):
                        place["distance"] = geodesic(
                            (latitude, longitude),
                            (place["position"]["lat"], place["position"]["lng"]),
                        ).meters
                        valid_places.append(place)
            except asyncio.TimeoutError:
                logger.debug("Widest search timed out, continuing with what we have")

        if not valid_places:
            await status_message.edit_text(
                "🐦 Well... Even us city birds don't hang around here much. Try dropping your pin somewhere else!"
            )
            return

        # Sort places by distance to get the 5 closest ones
        valid_places.sort(key=lambda x: x["distance"])

        # Take only the closest 5 places
        closest_places = valid_places[:5] if len(valid_places) >= 5 else valid_places

        # Store user data for callback handling
        user_data[user_id] = {
            "places": closest_places,
            "current_index": 0,
            "latitude": latitude,
            "longitude": longitude,
            "street": english_street,
            "city": english_city,
            "db": db,
            "last_message": None,  # Добавляем для хранения последнего сообщения
        }

        # Update the status message with the count of places found
        places_count_message = f"🐦 Spotted {len(closest_places)} cool spots nearby! Swooping down to check them out..."
        await status_message.edit_text(places_count_message)

        # Show the first (closest) place immediately
        await show_place(message, user_id, 0)

    except Exception as e:
        logger.error(f"Error in location handler: {e}", exc_info=True)
        await message.answer(f"🐦 Squawk! Please try again later.")


async def show_place(message, user_id, place_index):
    """Show information about a place with optimized data retrieval."""
    try:
        # Get user data
        if user_id not in user_data:
            await message.answer(
                "🐦 Sorry, I lost track of our journey! Can you share your location again?"
            )
            return

        data = user_data[user_id]
        places = data["places"]

        # Check if index is valid
        if place_index < 0 or place_index >= len(places):
            place_index = 0  # Reset to the first place

        # Update current index
        data["current_index"] = place_index

        # Get place data
        place = places[place_index]

        # Get place details
        place_lat = place["position"]["lat"]
        place_lng = place["position"]["lng"]

        # Check if address is still a placeholder or if we need translations
        needs_processing = (
            not "original_title" in place  # Never processed
            or place["address"].get("label")
            == "Address will be fetched"  # Address not fetched
            or "title" in place
            and place["title"] == place.get("original_title")  # Not translated
        )

        place_photo = None  # Initialize photo variable
        
        if needs_processing:
            # Create a progress message while processing
            processing_message = await message.answer(
                "🐦 Reading the signposts and street names..."
            )

            # Get detailed place information
            from app.google_maps import get_place_details, get_place_photo

            # Get detailed place info if we have a place_id
            if "id" in place:
                http_client = await get_http_client()
                place_details = await get_place_details(place["id"], http_client)

                if place_details:
                    # Update place with more details
                    if "formatted_address" in place_details:
                        detailed_address = place_details["formatted_address"]
                    else:
                        # Fallback to getting detailed address from coordinates
                        from app.google_maps import get_detailed_address

                        detailed_address, _ = await get_detailed_address(
                            place_lat, place_lng
                        )

                    # Store original values
                    if not "original_title" in place:
                        place["original_title"] = place["title"]
                    place["original_address"] = detailed_address

                    # Website URL if available
                    if "website" in place_details:
                        place["contacts"] = [{"www": place_details["website"]}]
                        
                    # Store photo reference if available
                    if "main_photo_reference" in place_details:
                        place["photo_reference"] = place_details["main_photo_reference"]
                        # Try to get photo
                        place_photo = await get_place_photo(place_details["main_photo_reference"], http_client=http_client)
                        # Add debug logging
                        if place_photo:
                            logger.debug(f"Successfully retrieved photo for {place_name}, size: {len(place_photo)} bytes")
                        else:
                            logger.debug(f"Failed to retrieve photo for place")

                    # Translate both place name and address concurrently
                    translation_tasks = [
                        translate_to_english(place["original_title"]),
                        translate_to_english(detailed_address),
                    ]

                    # Wait for both translations
                    english_name, english_address = await asyncio.gather(
                        *translation_tasks
                    )

                    # Store the translated values
                    place["title"] = english_name
                    place["address"] = {"label": english_address}
                else:
                    # Fallback to simpler address fetching if place details failed
                    from app.google_maps import get_detailed_address

                    detailed_address, _ = await get_detailed_address(
                        place_lat, place_lng
                    )

                    if not "original_title" in place:
                        place["original_title"] = place["title"]
                    place["original_address"] = detailed_address

                    translation_tasks = [
                        translate_to_english(place["original_title"]),
                        translate_to_english(detailed_address),
                    ]

                    english_name, english_address = await asyncio.gather(
                        *translation_tasks
                    )

                    place["title"] = english_name
                    place["address"] = {"label": english_address}

            # Delete the processing message
            try:
                await processing_message.delete()
            except Exception:
                # Ignore any error if message can't be deleted
                pass
        elif "photo_reference" in place and not place_photo:
            # If we already have a photo reference but need to get the photo again
            from app.google_maps import get_place_photo
            http_client = await get_http_client()
            place_photo = await get_place_photo(place["photo_reference"], http_client=http_client)
            # Add debug logging
            if place_photo:
                logger.debug(f"Retrieved cached photo, size: {len(place_photo)} bytes")
            else:
                logger.debug("Failed to retrieve cached photo")

        # Format with proper styling and emojis
        place_name = place["title"]
        original_name = place.get("original_title", place_name)
        place_address = place["address"]["label"]

        # Calculate distance in km
        distance_km = place["distance"] / 1000

        # Get place type
        place_type = place.get("type", "point of interest")

        # Create navigation buttons
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Tell me more", callback_data=f"more_{place_index}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=(
                            "➡️ Next location"
                            if place_index < len(places) - 1
                            else "🔄 Back to first"
                        ),
                        callback_data=f"next_{(place_index + 1) % len(places)}",
                    )
                ],
                # Add a Google Maps link button that opens in browser
                [
                    InlineKeyboardButton(
                        text="🗺️ Open in Google Maps",
                        url=f"https://www.google.com/maps/search/?api=1&query={place_lat},{place_lng}"
                    )
                ]
            ]
        )

        # Log the search in the database only once per place
        if data.get("db") and not place.get("logged", False):
            db = data["db"]
            db.log_search(
                user_id, place_name, place_type, place_lat, place_lng, data["city"]
            )
            place["logged"] = True

        # Format message
        message_text = f"<b>{place_name.upper()}</b> ({place_index + 1}/{len(places)})"

        # Show original name if different from translated name
        if original_name != place_name:
            message_text += f" (<i>{original_name}</i>)"

        message_text += f"\n📍 <b>Address:</b> <code>{place_address}</code>\n"
        message_text += f"🚶 <b>Distance:</b> {distance_km:.1f} km\n"
        message_text += f"🏷️ <b>Type:</b> {place_type}"

        # Add website only for museums and galleries, without preview
        if place_type in ["museum", "art_gallery", "gallery"]:
            place_url = place.get("contacts", [])
            if place_url:
                place_url = place_url[0].get("www", "url_not_found")
                if isinstance(place_url, list) and place_url:
                    place_url = place_url[0].get("value", "url_not_found")

                if place_url != "url_not_found":
                    message_text += f"\n🌐 <b>Website:</b> {place_url}"

        # If we have a photo, send it with the information
        if place_photo:
            logger.debug(f"Sending photo with caption for {place_name}")
            # Send as a photo with caption instead of a text message
            photo_file = BufferedInputFile(
                place_photo,
                filename=f"place_{place_index}.jpg"
            )
            
            # Check if we need to update an existing message or send a new one
            if data.get("last_message"):
                try:
                    # Cannot edit a text message to a photo message, so delete the old one
                    await data["last_message"].delete()
                except Exception as e:
                    logger.error(f"Error deleting previous message: {e}")
                
                # Send new photo message
                new_message = await message.answer_photo(
                    photo_file,
                    caption=message_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                data["last_message"] = new_message
            else:
                # Send initial photo message
                new_message = await message.answer_photo(
                    photo_file,
                    caption=message_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                data["last_message"] = new_message
        else:
            logger.debug(f"No photo available for {place_name}, sending text only")
            # No photo available, send text only
            if data.get("last_message"):
                try:
                    await data["last_message"].edit_text(
                        message_text, parse_mode="HTML", reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Error editing message: {e}")
                    new_message = await message.answer(
                        message_text, parse_mode="HTML", reply_markup=keyboard
                    )
                    data["last_message"] = new_message
            else:
                new_message = await message.answer(
                    message_text, parse_mode="HTML", reply_markup=keyboard
                )
                data["last_message"] = new_message

    except Exception as e:
        logger.error(f"Error in show_place: {e}", exc_info=True)
        await message.answer(
            "🐦 Squawk! There was an error showing this place. Please try again."
        )

# Добавляем обработчик для кнопки "Next location"
@router.callback_query(F.data.startswith("next_"))
async def handle_next_location(callback: CallbackQuery):
    """Handle 'next location' button press."""
    try:
        # Acknowledge the callback
        await callback.answer()
        
        user_id = callback.from_user.id
        
        # Parse the index from callback data
        _, index = callback.data.split("_")
        index = int(index)
        
        # Get user data
        if user_id not in user_data:
            await callback.message.answer(
                "🐦 Sorry, I lost track of our journey! Can you share your location again?"
            )
            return
        
        # Show the next place
        await show_place(callback.message, user_id, index)
        
    except Exception as e:
        logger.error(f"Error in next location handler: {e}", exc_info=True)
        await callback.message.answer(
            "🐦 Squawk! There was an error showing the next place. Please try again."
        )


@router.callback_query(F.data.startswith("more_"))
async def handle_tell_more(callback: CallbackQuery):
    """Handle 'tell me more' button press with rate limiting."""
    request_key = None  # Define this outside try block so it's available in except
    place_name = None   # Define this outside try block
    history = None      # Define this outside try block
    
    try:
        user_id = callback.from_user.id

        # Parse the index from callback data
        _, index = callback.data.split("_")
        index = int(index)

        # Get user data
        if user_id not in user_data:
            await callback.answer(
                "I lost track of our journey! Please share your location again.",
                show_alert=True,
            )
            return

        # Create a unique key for this request to prevent duplicates
        request_key = f"{user_id}_{index}"

        # Check if there's already an active request for this place
        if request_key in active_deepseek_requests:
            # Check if the request is still active
            if active_deepseek_requests[request_key]["active"]:
                # Inform the user that a request is already in progress
                await callback.answer(
                    "I'm still thinking about this place! Please wait a moment...",
                    show_alert=True,
                )
                return

            # Check cooldown period (300 seconds)
            last_request_time = active_deepseek_requests[request_key]["timestamp"]
            current_time = asyncio.get_event_loop().time()

            if current_time - last_request_time < 300:
                # Within cooldown period - don't allow new request
                remaining = int(300 - (current_time - last_request_time))
                await callback.answer(
                    f"I just told you about this place! Try again in {remaining} seconds.",
                    show_alert=True,
                )
                return

        # Acknowledge the callback
        await callback.answer("Let me gather my thoughts about this place...")

        data = user_data[user_id]
        place = data["places"][index]

        # Mark this request as active
        active_deepseek_requests[request_key] = {
            "active": True,
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Удаляем кнопку "Next location" из текущего сообщения
        # Оставляем только кнопку "Tell me more"
        current_message = callback.message
        new_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Tell me more", callback_data=f"more_{index}"
                    ),
                ]
            ]
        )
        try:
            await current_message.edit_reply_markup(reply_markup=new_keyboard)
        except Exception as e:
            logger.error(f"Error removing 'Next location' button: {e}")

        # Check if place has properly translated information
        if (
            not "title" in place
            or place["title"] == place.get("original_title")
            or place["address"].get("label") == "Address will be fetched"
        ):
            # Need to fetch and translate information first
            status_msg = await callback.message.answer(
                "🐦 Wait, let me check the details first..."
            )

            # Get place details
            place_lat = place["position"]["lat"]
            place_lng = place["position"]["lng"]

            # Get detailed address
            detailed_address, _ = await get_detailed_address(place_lat, place_lng)

            # Store original values
            if not "original_title" in place:
                place["original_title"] = place["title"]
            place["original_address"] = detailed_address

            # Translate both place name and address concurrently
            translation_tasks = [
                translate_to_english(place["original_title"]),
                translate_to_english(detailed_address),
            ]

            # Wait for both translations
            english_name, english_address = await asyncio.gather(*translation_tasks)

            # Store the translated values
            place["title"] = english_name
            place["address"] = {"label": english_address}

            # Delete status message
            try:
                await status_msg.delete()
            except Exception:
                pass

        # Get place details
        place_name = place["title"]
        original_name = place.get("original_title", place_name)
        place_address = place["address"]["label"]

        # Check if we already have history for this place
        if "history" in place and place["history"]:
            # Use cached history instead of making a new request
            history = place["history"]
            history_msg = await callback.message.answer(
                "🐦 I remember telling you about this place..."
            )
        else:
            # Get deepseek information
            history_msg = await callback.message.answer(
                "🐦 Digging into my memories about this place..."
            )
            history = await deepseek_location_info(
                data["city"], data["street"], place_name, place_address, original_name
            )
            # Cache the history for future requests
            place["history"] = history

        # Send history message
        history_message = f"<b>About {place_name}</b>\n\n<blockquote expandable>{history}</blockquote>"
        await callback.message.answer(history_message, parse_mode="HTML")

        # Try to delete the "digging into memories" message to keep chat clean
        try:
            await history_msg.delete()
        except Exception:
            pass

        # Generate audio and send if not already cached
        if not "audio_sent" in place or not place["audio_sent"]:
            audio_bytes = await yandex_speechkit_tts(history)

            # Send audio description
            if audio_bytes:
                if len(audio_bytes) > 50 * 1024 * 1024:
                    await callback.message.answer(
                        "The audio message is too large to send."
                    )
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
                                    "🐦 My vocal cords are tired from all this cooing! Try again when my voice recovers!"
                                )
                            await asyncio.sleep(2)

        # Mark request as completed
        active_deepseek_requests[request_key]["active"] = False

    except Exception as e:
        # Make sure to mark request as inactive even if an error occurs
        if request_key:
            active_deepseek_requests[request_key] = {
                "active": False,
                "timestamp": asyncio.get_event_loop().time(),
            }

        logger.error(f"Error in tell more handler: {e}", exc_info=True)
        await callback.message.answer(
            "🐦 Squawk! I forgot what I was going to say. Please try again."
        )
        
        # Only send history message if we have both place_name and history
        if place_name and history:
            # Send history message
            history_message = f"<b>About {place_name}</b>\n\n<blockquote expandable>{history}</blockquote>"
            await callback.message.answer(history_message, parse_mode="HTML")

            # Generate audio and send
            audio_bytes = await yandex_speechkit_tts(history)

            # Send audio description
            if audio_bytes:
                if len(audio_bytes) > 50 * 1024 * 1024:
                    await callback.message.answer("The audio message is too large to send.")
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
                                await callback.message.answer(
                                    "🐦 My vocal cords are tired from all this cooing! Try again when my voice recovers!"
                                )
                            await asyncio.sleep(2)

# Handle unknown commands or text messages
@router.message()
async def handle_unknown(message: Message, db=None):
    """Handle any other messages."""
    try:
        user_id = message.from_user.id

        # Update user's last active timestamp
        if db:
            db.add_or_update_user(
                user_id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name,
            )

        await message.answer(
            "🐦 I need coordinates to fly to, friend! Share your location or coo '/start' to begin our urban adventure!"
        )
    except Exception as e:
        logger.error(f"Error in unknown message handler: {e}", exc_info=True)
        await message.answer("An error occurred. Please try again later.")