import logging
import os
from dotenv import load_dotenv
import httpx
from geopy.distance import geodesic
import xmltodict

# Load environment variables
load_dotenv()

YANDEX_API_KEY = os.getenv("YA_TOKEN")
YA_MODELURI = os.getenv("YA_MODELURI")
YA_SPEECHKIT_API_KEY = os.getenv("YA_SPEECHKIT_API_KEY")
HERE_API_KEY = os.getenv("HERE_API_KEY")
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
    """
    https://yandex.cloud/ru/docs/search-api/concepts/pic-search
    https://yandex.cloud/ru/docs/search-api/concepts/get-request
    """

    if search_type not in YA_SEARCH_TYPES:
        return

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
                    print(len(image_groups))
                    return [result["doc"]["url"] for result in image_groups]
                elif search_type == "web":
                    print("Not implemented yet")
                    return []
            else:
                logging.error(
                    f"Yandex Search API error: {response.status_code} - {response.text}"
                )
                return []
    except Exception as e:
        logging.error(f"Exception in Yandex Search API: {str(e)}")
        return []


async def yandex_gpt_request(payload):
    """Send a request to Yandex GPT and return the response."""
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                alternatives = response.json().get("result", {}).get("alternatives", [])
                return (
                    alternatives[0]["message"].get("text", "Error: No text found.")
                    if alternatives
                    else "Error: Invalid response structure."
                )
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


async def here_maps_geocode(address: str):
    """Convert an address into geographic coordinates using HERE Geocoding API."""
    url = "https://geocode.search.hereapi.com/v1/geocode"
    params = {"q": address, "apiKey": HERE_API_KEY}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                items = response.json().get("items", [])
                return items[0]["position"] if items else None
            print(f"HERE Geocoding API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception in HERE Geocoding API: {str(e)}")
        return None


async def here_maps_nearby_places(
    latitude: float, longitude: float, category: str, radius: int = 1000
):
    """Fetch nearby places of a specific category using HERE Maps API."""
    url = "https://discover.search.hereapi.com/v1/discover"
    params = {
        "q": category,
        "in": f"circle:{latitude},{longitude};r={radius}",
        "apiKey": HERE_API_KEY,
        "lang": "en",  # Ensure results are in English
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                items = response.json().get("items", [])
                return [
                    item
                    for item in items
                    if geodesic(
                        (latitude, longitude),
                        (item["position"]["lat"], item["position"]["lng"]),
                    ).meters
                    <= radius
                ]
            print(f"HERE Maps API error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Exception in HERE Maps API: {str(e)}")
        return []


async def yandex_gpt_location_info(
    city: str, street: str, poi_name: str, poi_address: str
):
    """Generate a guided response using Yandex GPT, focusing on historical information about the POI."""
    if not all([city, street, poi_name]):
        return "Unable to generate a story due to insufficient information."

    payload = {
        "modelUri": YA_MODELURI,
        "completionOptions": {"stream": False, "temperature": 0.7, "maxTokens": 1000},
        "messages": [
            {
                "role": "system",
                "text": f"You are a historian and professional city guide. You are on {street} in {city}. Provide detailed historical information about {poi_name}, which is located at {poi_address}. Your story should be lively and coherent, with thoughts flowing into one another. Write at least 3 sentences. Use your imagination and creativity to make the story engaging and informative. Write in English",
            },
            {
                "role": "user",
                "text": f"Street: {street}, City: {city}, POI: {poi_name}, Address: {poi_address}",
            },
        ],
    }
    return await yandex_gpt_request(payload)


async def yandex_speechkit_tts(text: str):
    """Convert text to speech using Yandex SpeechKit."""
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    headers = {"Authorization": f"Api-Key {YA_SPEECHKIT_API_KEY}"}
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": "john",
        "format": "mp3",
        "folderId": "b1gjn47rcuokgs8tfom5",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data)
            return response.content if response.status_code == 200 else None
    except Exception as e:
        print(f"Exception in SpeechKit TTS: {str(e)}")
        return None
