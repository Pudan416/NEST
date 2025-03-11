import logging
import os
import asyncio
from dotenv import load_dotenv
import httpx
from geopy.distance import geodesic
import xmltodict

# Load environment variables
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
YA_SPEECHKIT_API_KEY = os.getenv("YA_SPEECHKIT_API_KEY")
YA_SEARCH_API_KEY = os.getenv("YA_SEARCH_API_KEY")
YA_CATALOG_ID = os.getenv("YA_CATALOG_ID")

YA_SEARCH_TYPES = ["web", "images"]


async def yandex_search(query: str, search_type: str = "images"):
    """
    Search for websites or images using Yandex Search API.
    :param query: The search query (e.g., place name).
    :param search_type: The type of search ("web" for websites, "images" for pictures).
    :return: A list of search results (websites or image URLs).
    """
    if search_type not in YA_SEARCH_TYPES:
        return []

    images_search_url = "https://yandex.com/images-xml"
    images_search_params = {
        "text": query,
        "folderid": YA_CATALOG_ID,
        "apikey": YA_SEARCH_API_KEY,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(images_search_url, params=images_search_params)
            if response.status_code == 200:
                data = xmltodict.parse(response.text)
                logging.debug(f"Yandex Search API response: {data}")
                if search_type == "images":
                    image_groups = data["yandexsearch"]["response"]["results"][
                        "grouping"
                    ]["group"]
                    return [result["doc"]["url"] for result in image_groups]
                elif search_type == "web":
                    return []
            else:
                logging.error(
                    f"Yandex Search API error: {response.status_code} - {response.text}"
                )
                return []
    except Exception as e:
        logging.error(f"Exception in Yandex Search API: {str(e)}")
        return []


async def deepseek_request(payload, max_retries=3):
    """Send a request to DeepSeek with retry logic and improved error handling."""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    if not DEEPSEEK_API_KEY:
        logging.error("DEEPSEEK_API_KEY is not set in environment variables")
        return "Error: DeepSeek API key is not configured. Please check your environment variables."

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logging.debug(
                    f"Sending request to DeepSeek API (attempt {attempt+1}/{max_retries})"
                )

                response = await client.post(url, headers=headers, json=payload)
                logging.debug(f"DeepSeek API response status: {response.status_code}")

                # Check for specific error status codes
                if response.status_code == 401:
                    logging.error("Authentication error: Invalid API key")
                    return "Error: Invalid API key. Please check your API credentials."

                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        retry_after = int(response.headers.get("retry-after", 1))
                        logging.warning(
                            f"Rate limited. Retrying after {retry_after} seconds"
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        return "Error: Rate limit exceeded. Please try again later."

                elif response.status_code == 200:
                    response_data = response.json()

                    # Extract content from the choices array
                    if "choices" in response_data and response_data["choices"]:
                        message = response_data["choices"][0].get("message", {})
                        content = message.get("content", "")
                        if content:
                            return content
                        else:
                            logging.error("No content found in DeepSeek response")
                            return "No content found in response."
                    else:
                        logging.error(f"Unexpected response format: {response_data}")
                        return "Error: Unexpected response format."
                else:
                    error_msg = f"API error: {response.status_code} - {response.text}"
                    logging.error(error_msg)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)  # Exponential backoff
                        continue
                    return f"Error: {error_msg}"

        except httpx.ConnectTimeout:
            logging.error(
                f"Connection timeout to DeepSeek API (attempt {attempt+1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff
                continue
            return "Error: Connection timeout. The API service might be unavailable."

        except httpx.ReadTimeout:
            logging.error(
                f"Read timeout from DeepSeek API (attempt {attempt+1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            return "Error: Read timeout. The request took too long to process."

        except Exception as e:
            error_msg = f"Exception in DeepSeek API request: {str(e)}"
            logging.error(error_msg)
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            return f"Error: {error_msg}"

    return "Error: Failed after multiple attempts to contact DeepSeek API."


async def test_deepseek_connection():
    """Test the connection to DeepSeek API."""
    simple_payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "max_tokens": 10,
    }
    result = await deepseek_request(simple_payload)
    logging.info(f"DeepSeek connection test result: {result}")
    return result


async def overpass_nearby_places(latitude: float, longitude: float, radius: int = 1000):
    """
    Fetch nearby tourist destinations using Overpass API with an expanded query
    to include more types of attractions.
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      // Tourism-related locations (excluding accommodations)
      node["tourism"]["tourism"!~"hotel|hostel|information|picnic_site|motel"](around:{radius},{latitude},{longitude});
      way["tourism"]["tourism"!~"hotel|hostel|information|picnic_site|motel"](around:{radius},{latitude},{longitude});
      relation["tourism"]["tourism"!~"hotel|hostel|information|picnic_site|motel"](around:{radius},{latitude},{longitude});
      
      // Historical sites
      node["historic"](around:{radius},{latitude},{longitude});
      way["historic"](around:{radius},{latitude},{longitude});
      relation["historic"](around:{radius},{latitude},{longitude});
      
      // Religious and cultural sites
      node["amenity"="place_of_worship"](around:{radius},{latitude},{longitude});
      way["amenity"="place_of_worship"](around:{radius},{latitude},{longitude});
      node["amenity"="theatre"](around:{radius},{latitude},{longitude});
      way["amenity"="theatre"](around:{radius},{latitude},{longitude});
      node["amenity"="arts_centre"](around:{radius},{latitude},{longitude});
      way["amenity"="arts_centre"](around:{radius},{latitude},{longitude});
      node["amenity"="cinema"](around:{radius},{latitude},{longitude});
      way["amenity"="cinema"](around:{radius},{latitude},{longitude});
      
      // Museums and galleries specifically
      node["tourism"="museum"](around:{radius},{latitude},{longitude});
      way["tourism"="museum"](around:{radius},{latitude},{longitude});
      node["tourism"="gallery"](around:{radius},{latitude},{longitude});
      way["tourism"="gallery"](around:{radius},{latitude},{longitude});
      
      // Monuments and memorials specifically
      node["historic"="monument"](around:{radius},{latitude},{longitude});
      way["historic"="monument"](around:{radius},{latitude},{longitude});
      node["historic"="memorial"](around:{radius},{latitude},{longitude});
      way["historic"="memorial"](around:{radius},{latitude},{longitude});
      
      // Parks and natural features
      node["leisure"="park"](around:{radius},{latitude},{longitude});
      way["leisure"="park"](around:{radius},{latitude},{longitude});
      
      // Viewpoints
      node["tourism"="viewpoint"](around:{radius},{latitude},{longitude});
      way["tourism"="viewpoint"](around:{radius},{latitude},{longitude});
      
      // Attractions
      node["tourism"="attraction"](around:{radius},{latitude},{longitude});
      way["tourism"="attraction"](around:{radius},{latitude},{longitude});
      
      // Notable buildings
      node["building"]["building"~"cathedral|church|mosque|synagogue|temple"](around:{radius},{latitude},{longitude});
      way["building"]["building"~"cathedral|church|mosque|synagogue|temple"](around:{radius},{latitude},{longitude});
    );
    out center;
    >;
    out skel qt;
    """

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(overpass_url, data=overpass_query)
            if response.status_code == 200:
                data = response.json()
                elements = data.get("elements", [])
                places = []

                for element in elements:
                    # Extract tags
                    tags = element.get("tags", {})

                    # Get coordinates
                    if element.get("type") == "node":
                        lat, lon = element.get("lat"), element.get("lon")
                    elif "center" in element:
                        lat, lon = element.get("center", {}).get("lat"), element.get(
                            "center", {}
                        ).get("lon")
                    else:
                        continue  # Skip if no coordinates

                    # Get place name
                    name = tags.get("name") or tags.get("name:en")
                    # Skip places without a name
                    if not name:
                        continue

                    # Get place type
                    place_type = (
                        tags.get("tourism")
                        or tags.get("historic")
                        or tags.get("amenity")
                        or tags.get("natural")
                        or tags.get("leisure")
                        or "point of interest"
                    )

                    # Create place object
                    place = {
                        "id": element.get("id"),
                        "title": name,
                        "type": place_type,
                        "position": {
                            "lat": lat,
                            "lng": lon,
                        },
                        "address": {"label": "Address will be fetched"},  # Placeholder
                        "contacts": [{"www": tags.get("website", "url_not_found")}],
                        "original_name": name,  # Store original name for reference
                    }
                    places.append(place)

                # Remove duplicates and unknown places
                unique_places = []
                seen = set()
                for place in places:
                    # Skip places with "Unknown" in the title
                    if "Unknown" in place["title"]:
                        continue

                    key = (
                        place["title"],
                        place["position"]["lat"],
                        place["position"]["lng"],
                    )
                    if key not in seen:
                        seen.add(key)
                        unique_places.append(place)

                return unique_places
            else:
                logging.error(
                    f"Overpass API error: {response.status_code} - {response.text}"
                )
                return []
    except Exception as e:
        logging.error(f"Exception in Overpass API: {str(e)}")
        return []


async def get_detailed_address(latitude: float, longitude: float):
    """Get a detailed address using Nominatim reverse geocoding."""
    nominatim_url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "addressdetails": 1,
        "accept-language": "en",  # Request English results when possible
    }

    try:
        # Use a custom User-Agent to be polite to the Nominatim service
        headers = {"User-Agent": "TouristGuideBot/1.0"}
        async with httpx.AsyncClient() as client:
            response = await client.get(nominatim_url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                address = data.get("address", {})

                # Format a complete address
                parts = []
                if "house_number" in address:
                    parts.append(address["house_number"])
                if "road" in address:
                    parts.append(address["road"])
                if "suburb" in address:
                    parts.append(address["suburb"])
                if "city" in address or "town" in address or "village" in address:
                    parts.append(
                        address.get("city")
                        or address.get("town")
                        or address.get("village")
                    )
                if "county" in address:
                    parts.append(address["county"])
                if "postcode" in address:
                    parts.append(address["postcode"])
                if "country" in address:
                    parts.append(address["country"])

                formatted_address = ", ".join(parts)
                return formatted_address, data
            else:
                logging.error(
                    f"Nominatim API error: {response.status_code} - {response.text}"
                )
                return "Address not available", {}
    except Exception as e:
        logging.error(f"Exception in Nominatim API: {str(e)}")
        return "Address not available", {}


async def translate_to_english(text: str):
    """Translate text to English using DeepSeek API."""
    if (
        not text
        or text.strip() == ""
        or text == "Address not specified"
        or text == "Address not available"
    ):
        return text

    payload = {
        "model": "deepseek-chat",
        "temperature": 0.3,  # Lower temperature for more accurate translations
        "max_tokens": 500,
        "messages": [
            {
                "role": "system",
                "content": "You are a professional translator. Translate the given text to English. Preserve proper nouns but translate everything else. Keep the translation concise and accurate. Only respond with the translation, nothing else.",
            },
            {"role": "user", "content": f"Translate this to English: {text}"},
        ],
    }

    result = await deepseek_request(payload)
    if result.startswith("Error:"):
        logging.error(f"Translation error: {result}")
        return text  # Return original text if translation fails

    return result


async def deepseek_location_info(
    city: str,
    street: str,
    poi_name: str,
    poi_address: str,
    original_poi_name: str = None,
):
    """Generate a guided response using DeepSeek, focusing on historical information about the POI."""
    # Include original name for context if it's different from the translated name
    context = (
        f"Original name: {original_poi_name}\n"
        if original_poi_name and original_poi_name != poi_name
        else ""
    )

    if not all([city, poi_name]):
        return "Unable to generate a story due to insufficient information."

    # Try different model options in case one doesn't work
    models = [
        "deepseek-chat",
        "deepseek-chat-v1",
        "deepseek-coder-33b-instruct",
        "deepseek-llm-67b-chat",
    ]

    # Try with first model, fallback to others if needed
    for model in models:
        payload = {
            "model": model,
            "temperature": 0.7,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a historian and professional city guide in {city}. "
                    f"Provide a concise historical overview of {poi_name}, located at {poi_address}. {context}"
                    f"Structure your response as follows: First make a short yet catchy explanation of the place, that teases what you will talk about later. "
                    f"Then follow this structure in your response: describe its appearance and key features; then tell proven historical facts about the place (if they exist), "
                    f"then share a verified historical detail; then explain its original purpose or significance; then describe its current role or use. "
                    f"Keep the response under 200 words, engaging, and informative. Use your imagination and creativity to bring the story to life. "
                    f"Use only English language throughout the entire response.",
                },
                {
                    "role": "user",
                    "content": f"Street: {street}, City: {city}, POI: {poi_name}, Address: {poi_address}",
                },
            ],
        }

        result = await deepseek_request(payload)
        if not result.startswith("Error:"):
            return result

        logging.warning(f"Failed with model {model}, trying next model if available")

    # If all models failed, return the last error
    return result


async def yandex_speechkit_tts(text: str):
    """Convert text to speech using Yandex SpeechKit."""
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    headers = {"Authorization": f"Api-Key {YA_SPEECHKIT_API_KEY}"}
    data = {
        "text": text,
        "lang": "en-US",  # Changed to English since our content is now in English
        "voice": "john",
        "format": "mp3",
        "folderId": "b1gjn47rcuokgs8tfom5",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data)
            return response.content if response.status_code == 200 else None
    except Exception as e:
        logging.error(f"Exception in SpeechKit TTS: {str(e)}")
        return None
