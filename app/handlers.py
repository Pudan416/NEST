import logging
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import CommandStart
from app.generators import (
    deepseek_location_info,
    overpass_nearby_places,
    yandex_speechkit_tts,
    yandex_search,
    test_deepseek_connection,
    get_detailed_address,
    translate_to_english,
)
import httpx
from geopy.distance import geodesic
import asyncio

router = Router()
logging.basicConfig(level=logging.DEBUG)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


@router.message(CommandStart())
async def handle_start_command(message: Message):
    """Handle the /start command."""
    try:
        logging.debug(f"Received '/start' command from user: {message.from_user.id}")
        await message.answer(
            "Welcome! Please share your location to find nearby tourist attractions."
        )
    except Exception as e:
        logging.error(f"Error in '/start' command handler: {e}")
        await message.answer("An error occurred. Please try again later.")


@router.message(F.text == "/test_api")
async def handle_test_api(message: Message):
    """Test the DeepSeek API connection."""
    try:
        await message.answer("Testing DeepSeek API connection...")
        result = await test_deepseek_connection()
        await message.answer(f"DeepSeek API test result: {result}")
    except Exception as e:
        logging.error(f"Error in API test handler: {e}")
        await message.answer(f"Error testing API: {str(e)}")


@router.message(F.location)
async def handle_location(message: Message):
    """Handle location messages and provide information about nearby tourist attractions."""
    try:
        latitude, longitude = message.location.latitude, message.location.longitude

        # Send initial status message and store the message object to edit it later
        status_message = await message.answer(
            "🔍 Looking for interesting places nearby..."
        )

        # Get user's current location details
        address, address_data = await get_detailed_address(latitude, longitude)
        address_parts = address_data.get("address", {})
        street = address_parts.get("road", "Unknown Street")
        city = address_parts.get(
            "city",
            address_parts.get("town", address_parts.get("village", "Unknown City")),
        )

        # Translate street and city names to English
        english_street = await translate_to_english(street)
        english_city = await translate_to_english(city)

        logging.debug(f"Current location: {street}, {city}")
        logging.debug(f"Translated location: {english_street}, {english_city}")

        # Find nearby places with a 10km radius
        places = await overpass_nearby_places(latitude, longitude, radius=10000)

        if not places:
            # Update status message
            await status_message.edit_text(
                "No tourist attractions found nearby. Trying a wider search..."
            )
            places = await overpass_nearby_places(
                latitude, longitude, radius=20000
            )  # Increase to 20km

            if not places:
                # Update status message again
                await status_message.edit_text(
                    "No named tourist attractions found. Trying a wider search with more options..."
                )
                places = await overpass_nearby_places(
                    latitude, longitude, radius=30000
                )  # Increase to 30km

        # Filter and calculate distance for valid places
        valid_places = []
        for place in places:
            # Skip places with "unknown" in the title (case insensitive)
            if "unknown" in place["title"].lower():
                continue

            place["distance"] = geodesic(
                (latitude, longitude),
                (place["position"]["lat"], place["position"]["lng"]),
            ).meters
            valid_places.append(place)

        if not valid_places:
            await status_message.edit_text(
                "No identifiable tourist attractions found nearby. Please try a different location."
            )
            return

        # Sort places by distance and get the closest one
        valid_places.sort(key=lambda x: x["distance"])
        closest_place = valid_places[0]

        # Update the status message with the count of valid places
        await status_message.edit_text(
            f"Found {len(valid_places)} interesting places nearby! Showing the closest one..."
        )

        # Process the closest place: get address and translate
        place_lat = closest_place["position"]["lat"]
        place_lng = closest_place["position"]["lng"]

        # Get detailed address
        detailed_address, _ = await get_detailed_address(place_lat, place_lng)

        # Save original values before translation
        closest_place["original_title"] = closest_place["title"]
        closest_place["original_address"] = detailed_address

        # Translate place name and address to English
        closest_place["title"] = await translate_to_english(closest_place["title"])
        closest_place["address"]["label"] = await translate_to_english(detailed_address)

        # Prepare place details
        place_name = closest_place["title"]
        original_name = closest_place.get("original_title", place_name)
        place_address = closest_place["address"]["label"]
        original_address = closest_place.get("original_address", place_address)

        # Handle website URL
        place_url = closest_place.get("contacts", [])
        if place_url:
            place_url = place_url[0].get("www", "url_not_found")
            if isinstance(place_url, list) and place_url:
                place_url = place_url[0].get("value", "url_not_found")
        else:
            place_url = "url_not_found"

        # Get place type and distance
        place_type = closest_place.get("type", "point of interest")
        distance = closest_place.get("distance", 0)
        distance_km = distance / 1000

        # Get historical information from DeepSeek
        history = await deepseek_location_info(
            english_city, english_street, place_name, place_address, original_name
        )

        # Search for images
        search_query = f"{place_name} {english_city}"
        images = await yandex_search(search_query, search_type="images")

        # Format message with English name and original name if different
        message_text = f"<b>{place_name.upper()}</b>"

        # Show original name if different from translated name
        if original_name != place_name:
            message_text += f" (<i>{original_name}</i>)"

        message_text += f"\n📍 <b>Address:</b> <code>{place_address}</code>\n"
        message_text += f"🚶 <b>Distance:</b> {distance_km:.1f} km\n"
        message_text += f"🏷️ <b>Type:</b> {place_type}\n\n"

        if place_url != "url_not_found":
            message_text += (
                f"🌐 <b>Webpage:</b> <a href='{place_url}'>{place_url}</a>\n\n"
            )

        message_text += f"<blockquote expandable>{history}</blockquote>"

        # Replace the status message with the actual detailed information
        await status_message.edit_text(message_text, parse_mode="HTML")

        # Generate and send audio description
        audio_bytes = await yandex_speechkit_tts(history)
        if audio_bytes:
            if len(audio_bytes) > 50 * 1024 * 1024:
                await message.answer("The audio message is too large to send.")
            else:
                for attempt in range(3):
                    try:
                        audio_file = BufferedInputFile(
                            audio_bytes, filename="voice_message.mp3"
                        )
                        await message.answer_voice(voice=audio_file)
                        break
                    except Exception as e:
                        if attempt == 2:
                            logging.error(f"Failed to send audio after 3 attempts: {e}")
                            await message.answer(
                                "Failed to send the audio message. Please try again later."
                            )
                        await asyncio.sleep(2)

        # Send image if found
        if images:
            try:
                await message.answer_photo(images[0])
            except Exception as e:
                logging.error(f"Failed to send image: {e}")
                await message.answer("Couldn't load the image for this place.")
        else:
            await message.answer("No pictures found for this place.")

    except Exception as e:
        logging.error(f"Error in location handler: {e}")
        await message.answer(f"An error occurred. Please try again later.")
