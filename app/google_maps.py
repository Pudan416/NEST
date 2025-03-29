import os
from typing import List, Dict, Any, Tuple
import httpx
from app import logger
from app.texts import API_MESSAGES, GOOGLE_MAPS_MESSAGES

# API endpoints
PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Supported place types
SUPPORTED_PLACE_TYPES = [
    "tourist_attraction",
    "museum",
    "art_gallery", 
    "church",
    "hindu_temple",
    "mosque",
    "synagogue",
    "park",
    "amusement_park",
    "aquarium",
    "campground",
    "zoo"
]

async def search_places_by_text(
    query: str, http_client: httpx.AsyncClient = None
) -> List[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return []

    places = []
    should_close_client = False
    
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True
    
    try:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.websiteUri"
        }
        
        request_body = {
            "textQuery": query,
            "languageCode": "en"
        }
        
        logger.debug(f"Places API request: URL={TEXT_SEARCH_URL}, Headers={headers}, Body={request_body}")
        
        response = await http_client.post(
            TEXT_SEARCH_URL,
            json=request_body,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("places"):
                for place in data.get("places", []):
                    place_type = "tourist_attraction"
                    if place.get("types") and len(place.get("types")) > 0:
                        for t in place.get("types"):
                            if t in SUPPORTED_PLACE_TYPES:
                                place_type = t
                                break
                    
                    formatted_place = {
                        "id": place.get("id"),
                        "title": place.get("displayName", {}).get("text", GOOGLE_MAPS_MESSAGES['unknown_place']),
                        "type": place_type,
                        "position": {
                            "lat": place.get("location", {}).get("latitude", 0),
                            "lng": place.get("location", {}).get("longitude", 0),
                        },
                        "address": {
                            "label": place.get("formattedAddress", GOOGLE_MAPS_MESSAGES['address_fetch'])
                        },
                        "contacts": [
                            {"www": place.get("websiteUri", GOOGLE_MAPS_MESSAGES['url_not_found'])}
                        ],
                    }
                    
                    places.append(formatted_place)
            else:
                logger.warning(f"No places found in Places API response: {data}")
        else:
            logger.error(
                f"Places API error: {response.status_code} - {response.text[:200]}"
            )
    except Exception as e:
        logger.error(f"Error in Places API text search: {str(e)}", exc_info=True)
    finally:
        if should_close_client:
            await http_client.aclose()
    
    return places


async def get_nearby_places(
    latitude: float,
    longitude: float,
    radius: int = 1000,
    place_types: List[str] = None,
    http_client: httpx.AsyncClient = None,
) -> List[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return []

    if not place_types:
        place_types = SUPPORTED_PLACE_TYPES
    else:
        place_types = [t for t in place_types if t in SUPPORTED_PLACE_TYPES]
        if not place_types:
            logger.warning("No supported place types found in the requested types")
            place_types = ["tourist_attraction", "museum"]

    places = []
    should_close_client = False
    
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True
    
    try:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.websiteUri"
        }
        
        for place_type in place_types:
            request_body = {
                "locationRestriction": {
                    "circle": {
                        "center": {"latitude": latitude, "longitude": longitude},
                        "radius": float(radius)
                    }
                },
                "includedTypes": [place_type],
                "languageCode": "en"
            }
            
            logger.debug(f"Places API request: URL={PLACES_NEARBY_URL}, Headers={headers}, Body={request_body}")
            
            response = await http_client.post(
                PLACES_NEARBY_URL,
                json=request_body,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("places"):
                    for place in data.get("places", []):
                        formatted_place = {
                            "id": place.get("id"),
                            "title": place.get("displayName", {}).get("text", GOOGLE_MAPS_MESSAGES['unknown_place']),
                            "type": place_type,
                            "position": {
                                "lat": place.get("location", {}).get("latitude", 0),
                                "lng": place.get("location", {}).get("longitude", 0),
                            },
                            "address": {
                                "label": place.get("formattedAddress", GOOGLE_MAPS_MESSAGES['address_fetch'])
                            },
                            "contacts": [
                                {"www": place.get("websiteUri", GOOGLE_MAPS_MESSAGES['url_not_found'])}
                            ],
                        }
                        
                        if not any(p["id"] == formatted_place["id"] for p in places):
                            places.append(formatted_place)
                else:
                    logger.debug(f"No places found for type {place_type}")
            else:
                logger.error(
                    f"Places API error for {place_type}: {response.status_code} - {response.text[:200]}"
                )
    except Exception as e:
        logger.error(f"Error in Places API nearby search: {str(e)}", exc_info=True)
    finally:
        if should_close_client:
            await http_client.aclose()
    
    return places


async def get_place_details(
    place_id: str, http_client: httpx.AsyncClient = None
) -> Dict[str, Any]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return {}
    
    details = {}
    should_close_client = False
    
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True
    
    try:
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "displayName,formattedAddress,websiteUri,types,photos,internationalPhoneNumber,googleMapsUri,nationalPhoneNumber,regularOpeningHours,businessStatus,userRatingCount,rating,priceLevel,editorialSummary"
        }
        
        url = f"{PLACE_DETAILS_URL}/{place_id}"
        logger.debug(f"Places API request: URL={url}, Headers={headers}")
        
        response = await http_client.get(
            url,
            headers=headers
        )
        
        if response.status_code == 200:
            place_data = response.json()
            
            details = {
                "name": place_data.get("displayName", {}).get("text", GOOGLE_MAPS_MESSAGES['unknown_place']),
                "formatted_address": place_data.get("formattedAddress", ""),
                "website": place_data.get("websiteUri", ""),
                "phone": {
                    "international": place_data.get("internationalPhoneNumber", ""),
                    "national": place_data.get("nationalPhoneNumber", "")
                },
                "types": place_data.get("types", []),
                "map_url": place_data.get("googleMapsUri", ""),
                "business_status": place_data.get("businessStatus", ""),
                "rating": {
                    "score": place_data.get("rating", 0),
                    "user_count": place_data.get("userRatingCount", 0)
                },
                "price_level": place_data.get("priceLevel", ""),
                "description": place_data.get("editorialSummary", {}).get("text", ""),
                "opening_hours": [],
                "photos": []
            }
            
            if "photos" in place_data and place_data["photos"]:
                photo_references = []
                for photo in place_data["photos"]:
                    if "name" in photo:
                        photo_references.append(photo["name"])
                
                details["photo_references"] = photo_references
                
                if photo_references:
                    details["main_photo_reference"] = photo_references[0]
            
            if place_data.get("regularOpeningHours", {}).get("periods"):
                for period in place_data["regularOpeningHours"]["periods"]:
                    if "open" in period and "day" in period["open"]:
                        day = period["open"]["day"]
                        
                        open_hour = period["open"].get("hour", "00")
                        open_minute = period["open"].get("minute", "00")
                        if isinstance(open_hour, int):
                            open_hour = str(open_hour).zfill(2)
                        if isinstance(open_minute, int):
                            open_minute = str(open_minute).zfill(2)
                        
                        open_time = f"{open_hour}:{open_minute}"
                        
                        close_time = "24:00"
                        if "close" in period:
                            close_hour = period["close"].get("hour", "00")
                            close_minute = period["close"].get("minute", "00")
                            if isinstance(close_hour, int):
                                close_hour = str(close_hour).zfill(2)
                            if isinstance(close_minute, int):
                                close_minute = str(close_minute).zfill(2)
                            
                            close_time = f"{close_hour}:{close_minute}"
                        
                        details["opening_hours"].append({
                            "day": day,
                            "open": open_time,
                            "close": close_time
                        })
        else:
            logger.error(
                f"Places API error for place details: {response.status_code} - {response.text[:200]}"
            )
    except Exception as e:
        logger.error(f"Error in Places API place details: {str(e)}", exc_info=True)
    finally:
        if should_close_client:
            await http_client.aclose()
    
    return details


async def get_detailed_address(
    latitude: float, longitude: float, http_client: httpx.AsyncClient = None
) -> Tuple[str, Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return GOOGLE_MAPS_MESSAGES['address_not_available'], {}

    try:
        params = {
            "latlng": f"{latitude},{longitude}",
            "key": api_key,
            "language": "en",
        }
        
        logger.debug(f"Geocoding API request: URL={GEOCODING_URL}, Params={params}")

        should_close_client = False
        if not http_client:
            http_client = httpx.AsyncClient(timeout=30.0)
            should_close_client = True

        try:
            response = await http_client.get(GEOCODING_URL, params=params)

            if response.status_code == 200:
                data = response.json()

                if data.get("status") == "OK" and data.get("results"):
                    result = data["results"][0]
                    formatted_address = result.get(
                        "formatted_address", GOOGLE_MAPS_MESSAGES['address_not_available']
                    )

                    address_components = {}
                    for component in result.get("address_components", []):
                        types = component.get("types", [])
                        
                        if "street_number" in types:
                            address_components["street_number"] = component.get("long_name", "")
                        elif "route" in types:
                            address_components["street"] = component.get("long_name", "")
                        elif "locality" in types:
                            address_components["city"] = component.get("long_name", "")
                        elif "administrative_area_level_1" in types:
                            address_components["state"] = component.get("long_name", "")
                        elif "country" in types:
                            address_components["country"] = component.get("long_name", "")
                            address_components["country_code"] = component.get("short_name", "")
                        elif "postal_code" in types:
                            address_components["postal_code"] = component.get("long_name", "")
                        elif "sublocality_level_1" in types:
                            address_components["district"] = component.get("long_name", "")
                        elif "administrative_area_level_2" in types:
                            address_components["county"] = component.get("long_name", "")

                    address_data = {
                        "formatted_address": formatted_address,
                        "address": address_components,
                        "location": {
                            "lat": result.get("geometry", {}).get("location", {}).get("lat", latitude),
                            "lng": result.get("geometry", {}).get("location", {}).get("lng", longitude)
                        }
                    }

                    return formatted_address, address_data
                else:
                    logger.error(f"Google Geocoding API error: {data.get('status')}")
            else:
                logger.error(
                    f"Google Geocoding API error: {response.status_code} - {response.text[:200]}"
                )
        finally:
            if should_close_client:
                await http_client.aclose()

    except Exception as e:
        logger.error(f"Exception in Google Geocoding API: {str(e)}", exc_info=True)

    return GOOGLE_MAPS_MESSAGES['address_not_available'], {}


async def get_place_photo(
    photo_reference: str, max_width: int = 600, http_client: httpx.AsyncClient = None
) -> bytes:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return None
        
    should_close_client = False
    
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        should_close_client = True
    
    try:
        logger.debug(f"Getting place photo for reference: {photo_reference}")
        
        if not photo_reference or not isinstance(photo_reference, str):
            logger.error(f"Invalid photo reference: {photo_reference}")
            return None
            
        url = f"https://places.googleapis.com/v1/{photo_reference}/media"
        
        headers = {
            "X-Goog-Api-Key": api_key,
            "Accept": "image/*"
        }
        
        params = {
            "maxWidthPx": max_width
        }
        
        logger.debug(f"Place Photo API request: URL={url}, Headers={headers}, Params={params}")
        
        response = await http_client.get(
            url,
            headers=headers,
            params=params,
            follow_redirects=True
        )
        
        logger.debug(f"Response status: {response.status_code}, Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            logger.debug(f"Successfully retrieved photo, size: {len(response.content)} bytes")
            
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('image/'):
                return response.content
            else:
                logger.error(f"Received non-image content type: {content_type}")
                logger.error(f"First 100 bytes of response: {response.content[:100]}")
                return None
        else:
            logger.error(
                f"Place Photo API error: {response.status_code} - {response.text[:200]}"
            )
            return None
    except Exception as e:
        logger.error(f"Error in Place Photo API: {str(e)}", exc_info=True)
        return None
    finally:
        if should_close_client:
            await http_client.aclose()


async def test_connection():
    try:
        test_lat, test_lng = 44.802416, 20.465601
        
        http_client = httpx.AsyncClient(timeout=30.0)
        
        try:
            logger.info("Testing Places API Text Search...")
            text_places = await search_places_by_text(GOOGLE_MAPS_MESSAGES['test_query'], http_client)
            if text_places:
                text_result = GOOGLE_MAPS_MESSAGES['text_search_success'].format(count=len(text_places))
            else:
                text_result = GOOGLE_MAPS_MESSAGES['text_search_failure']
            
            logger.info("Testing Places API Nearby Search...")
            nearby_places = await get_nearby_places(
                test_lat, test_lng, radius=500, 
                place_types=["tourist_attraction", "museum"], 
                http_client=http_client
            )
            
            if nearby_places:
                nearby_result = GOOGLE_MAPS_MESSAGES['nearby_search_success'].format(count=len(nearby_places))
                
                if nearby_places[0].get("id"):
                    logger.info(f"Testing Places API Details for place: {nearby_places[0]['id']}...")
                    place_details = await get_place_details(
                        nearby_places[0]["id"], http_client=http_client
                    )
                    if place_details:
                        details_result = GOOGLE_MAPS_MESSAGES['details_success']
                    else:
                        details_result = GOOGLE_MAPS_MESSAGES['details_failure']
                else:
                    details_result = GOOGLE_MAPS_MESSAGES['no_place_id']
            else:
                nearby_result = GOOGLE_MAPS_MESSAGES['nearby_search_failure']
                details_result = GOOGLE_MAPS_MESSAGES['details_skipped']
                
            logger.info("Testing Geocoding API...")
            address, address_data = await get_detailed_address(
                test_lat, test_lng, http_client=http_client
            )
            if address != GOOGLE_MAPS_MESSAGES['address_not_available']:
                geocoding_result = GOOGLE_MAPS_MESSAGES['geocoding_success'].format(address=address)
            else:
                geocoding_result = GOOGLE_MAPS_MESSAGES['geocoding_failure']
                
            return GOOGLE_MAPS_MESSAGES['test_results'].format(
                text_result=text_result,
                nearby_result=nearby_result,
                details_result=details_result,
                geocoding_result=geocoding_result,
                test_lat=test_lat,
                test_lng=test_lng
            )
        finally:
            await http_client.aclose()
    except Exception as e:
        return GOOGLE_MAPS_MESSAGES['test_failed'].format(error=str(e))