import logging
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import CommandStart
from app.generators import yandex_gpt_location_info, here_maps_nearby_places, yandex_speechkit_tts
import httpx
from app.generators import yandex_search
from geopy.distance import geodesic
import asyncio

router = Router()
logging.basicConfig(level=logging.DEBUG)

# Define the Nominatim API URL
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

# Define categories for tourist attractions
TOURIST_ATTRACTIONS_CATEGORY = "tourist_attraction|museum|gallery|monument|park|cathedral|church"

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

@router.message(F.location)
async def handle_location(message: Message):
    """Handle location messages and provide information about nearby tourist attractions."""
    try:
        latitude, longitude = message.location.latitude, message.location.longitude
        params = {"lat": latitude, "lon": longitude, "format": "json", "addressdetails": 1}

        async with httpx.AsyncClient() as client:
            response = await client.get(NOMINATIM_URL, params=params)
            if response.status_code != 200:
                await message.answer("Unable to determine your location. Please try again.")
                return

            data = response.json()
            address = data.get("address", {})
            street = address.get("road", "Unknown Street")
            city = address.get("city", address.get("town", "Unknown City"))

            if street == "Unknown Street":
                await message.answer("I couldn't identify the street. Please provide a more precise location or specify the street and city.")
                return

            places = await here_maps_nearby_places(latitude, longitude, TOURIST_ATTRACTIONS_CATEGORY)
            if not places:
                await message.answer("No tourist attractions found nearby.")
                return

            closest_place = min(places, key=lambda x: geodesic((latitude, longitude), (x["position"]["lat"], x["position"]["lng"])).meters)
            place_name = closest_place.get("title", "Unknown Place")
            place_address = closest_place.get("address", {}).get("label", "Address not specified")

            if place_name == "Unknown Place":
                await message.answer("I couldn't identify the nearest tourist attraction.")
                return

            # Remove the place name from the address
            # Split the address by commas and remove the first part (place name)
            address_parts = place_address.split(', ')
            if len(address_parts) > 1:
                place_address = ', '.join(address_parts[1:])  # Join the remaining parts

            # Generate historical info
            history = await yandex_gpt_location_info(city, street, place_name, place_address)

            # Search for websites and images
            search_query = f"{place_name} {city}"
            websites = await yandex_search(search_query, search_type="web")
            images = await yandex_search(search_query, search_type="images")

            # Prepare the unified text message
            message_text = f"<b>{place_name.upper()}</b>\n"  # Name of the place in CAPITALS and bold
            message_text += f"<code>{place_address}</code>\n\n"  # Address in monospace (using HTML <code>)

            if websites:
                message_text += f"Webpage: {websites[0]}\n\n"  # Webpage (if found)

            # Add GPT explanation as a blockquote (using HTML <blockquote>)
            message_text += f"<blockquote expandable>{history}</blockquote>"

            # Send the unified text message using HTML formatting
            await message.answer(message_text, parse_mode="HTML")

            # Convert GPT part to speech and send as audio
            audio_bytes = await yandex_speechkit_tts(history)
            if audio_bytes:
                if len(audio_bytes) > 50 * 1024 * 1024:
                    await message.answer("The audio message is too large to send.")
                else:
                    for attempt in range(3):
                        try:
                            audio_file = BufferedInputFile(audio_bytes, filename="voice_message.mp3")
                            await message.answer_voice(voice=audio_file)
                            break
                        except Exception as e:
                            if attempt == 2:
                                logging.error(f"Failed to send audio after 3 attempts: {e}")
                                await message.answer("Failed to send the audio message. Please try again later.")
                            await asyncio.sleep(2)
            else:
                await message.answer("Failed to generate the audio message.")

            # Send the first image if found
            if images:
                await message.answer_photo(images[0])
            else:
                await message.answer("No pictures found for this place.")

    except Exception as e:
        logging.error(f"Error in location handler: {e}")
        await message.answer("An error occurred. Please try again later.")