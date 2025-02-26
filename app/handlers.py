import logging
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import CommandStart
from app.generators import (
    yandex_gpt_location_info,
    overpass_nearby_places,
    yandex_speechkit_tts,
)
import httpx
from app.generators import yandex_search
from geopy.distance import geodesic
import asyncio

router = Router()
logging.basicConfig(level=logging.DEBUG)

# Define the Nominatim API URL
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


@router.message(F.location)
async def handle_location(message: Message):
    """Handle location messages and provide information about nearby tourist attractions."""
    try:
        latitude, longitude = message.location.latitude, message.location.longitude
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "addressdetails": 1,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(NOMINATIM_URL, params=params)
            if response.status_code != 200:
                await message.answer(
                    "Unable to determine your location. Please try again."
                )
                return

            data = response.json()
            address = data.get("address", {})
            street = address.get("road", "Unknown Street")
            city = address.get("city", address.get("town", "Unknown City"))

            if street == "Unknown Street":
                await message.answer(
                    "I couldn't identify the street. Please provide a more precise location or specify the street and city."
                )
                return

            places = await overpass_nearby_places(latitude, longitude)
            if not places:
                await message.answer("No tourist attractions found nearby.")
                return

            closest_place = min(
                places,
                key=lambda x: geodesic(
                    (latitude, longitude), (x["position"]["lat"], x["position"]["lng"])
                ).meters,
            )
            place_name = closest_place.get("title", "Unknown Place")
            place_address = closest_place.get("address", {}).get(
                "label", "Address not specified"
            )

            # Extract the first URL if multiple are present
            place_url = closest_place.get("contacts", [])
            if place_url:
                place_url = place_url[0].get("www", "url_not_found")
                if isinstance(place_url, list):
                    place_url = place_url[0].get("value", "url_not_found")
            else:
                place_url = "url_not_found"

            if place_name == "Unknown Place":
                await message.answer(
                    "I couldn't identify the nearest tourist attraction."
                )
                return

            # Generate historical info
            history = await yandex_gpt_location_info(
                city, street, place_name, place_address
            )

            # Search for websites and images
            search_query = f"{place_name} {city}"
            images = await yandex_search(search_query, search_type="images")

            # Prepare the unified text message
            message_text = f"<b>{place_name.upper()}</b>\n"  # Name of the place in CAPITALS and bold
            message_text += f"📍 <b>Address:</b> <code>{place_address}</code>\n\n"  # Address in monospace (using HTML <code>)
            if place_url != "url_not_found":
                message_text += f"🌐 <b>Webpage:</b> <a href='{place_url}'>{place_url}</a>\n\n"  # Webpage as a clickable link
            else:
                message_text += "🌐 <b>Webpage:</b> Not Found\n\n"

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
                            audio_file = BufferedInputFile(
                                audio_bytes, filename="voice_message.mp3"
                            )
                            await message.answer_voice(voice=audio_file)
                            break
                        except Exception as e:
                            if attempt == 2:
                                logging.error(
                                    f"Failed to send audio after 3 attempts: {e}"
                                )
                                await message.answer(
                                    "Failed to send the audio message. Please try again later."
                                )
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