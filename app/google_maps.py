"""
Google Maps API integration module.
"""

import os
from typing import List, Dict, Any, Tuple
import httpx
from app import logger
from app.languages import get_api_message

# API endpoints
PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DIRECTIONS_API_URL = "https://maps.googleapis.com/maps/api/directions/json"

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
    "zoo",
]


async def search_places_by_text(
    query: str, http_client: httpx.AsyncClient = None
) -> List[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error(get_api_message("google_maps_api_key_error"))
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
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.websiteUri",
        }

        request_body = {"textQuery": query, "languageCode": "en"}

        logger.debug(
            f"Places API request: URL={TEXT_SEARCH_URL}, Headers={headers}, Body={request_body}"
        )

        response = await http_client.post(
            TEXT_SEARCH_URL, json=request_body, headers=headers
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
                        "title": place.get("displayName", {}).get(
                            "text", get_api_message("unknown_place")
                        ),
                        "type": place_type,
                        "position": {
                            "lat": place.get("location", {}).get("latitude", 0),
                            "lng": place.get("location", {}).get("longitude", 0),
                        },
                        "address": {
                            "label": place.get(
                                "formattedAddress",
                                get_api_message("address_fetch"),
                            )
                        },
                        "contacts": [
                            {
                                "www": place.get(
                                    "websiteUri", get_api_message("url_not_found")
                                )
                            }
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
        logger.error(get_api_message("google_maps_api_key_error"))
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
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.websiteUri",
        }

        for place_type in place_types:
            request_body = {
                "locationRestriction": {
                    "circle": {
                        "center": {"latitude": latitude, "longitude": longitude},
                        "radius": float(radius),
                    }
                },
                "includedTypes": [place_type],
                "languageCode": "en",
            }

            logger.debug(
                f"Places API request: URL={PLACES_NEARBY_URL}, Headers={headers}, Body={request_body}"
            )

            response = await http_client.post(
                PLACES_NEARBY_URL, json=request_body, headers=headers
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("places"):
                    for place in data.get("places", []):
                        formatted_place = {
                            "id": place.get("id"),
                            "title": place.get("displayName", {}).get(
                                "text", get_api_message("unknown_place")
                            ),
                            "type": place_type,
                            "position": {
                                "lat": place.get("location", {}).get("latitude", 0),
                                "lng": place.get("location", {}).get("longitude", 0),
                            },
                            "address": {
                                "label": place.get(
                                    "formattedAddress",
                                    get_api_message("address_fetch"),
                                )
                            },
                            "contacts": [
                                {
                                    "www": place.get(
                                        "websiteUri",
                                        get_api_message("url_not_found"),
                                    )
                                }
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
        logger.error(get_api_message("google_maps_api_key_error"))
        return {}

    details = {}
    should_close_client = False

    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True

    try:
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "displayName,formattedAddress,websiteUri,types,photos,internationalPhoneNumber,googleMapsUri,nationalPhoneNumber,regularOpeningHours,businessStatus,userRatingCount,rating,priceLevel,editorialSummary",
        }

        url = f"{PLACE_DETAILS_URL}/{place_id}"
        logger.debug(f"Places API request: URL={url}, Headers={headers}")

        response = await http_client.get(url, headers=headers)

        if response.status_code == 200:
            place_data = response.json()

            details = {
                "name": place_data.get("displayName", {}).get(
                    "text", get_api_message("unknown_place")
                ),
                "address": place_data.get(
                    "formattedAddress", get_api_message("address_fetch")
                ),
                "website": place_data.get(
                    "websiteUri", get_api_message("url_not_found")
                ),
                "types": place_data.get("types", []),
                "photos": place_data.get("photos", []),
                "phone": place_data.get(
                    "internationalPhoneNumber",
                    place_data.get("nationalPhoneNumber", ""),
                ),
                "maps_url": place_data.get("googleMapsUri", ""),
                "opening_hours": place_data.get("regularOpeningHours", {}),
                "business_status": place_data.get("businessStatus", ""),
                "rating": place_data.get("rating", 0),
                "user_ratings_total": place_data.get("userRatingCount", 0),
                "price_level": place_data.get("priceLevel", ""),
                "editorial_summary": place_data.get("editorialSummary", {}).get(
                    "text", ""
                ),
            }
        else:
            logger.error(
                f"Places API error: {response.status_code} - {response.text[:200]}"
            )
    except Exception as e:
        logger.error(f"Error in Places API details: {str(e)}", exc_info=True)
    finally:
        if should_close_client:
            await http_client.aclose()

    return details


async def get_detailed_address(
    latitude: float, longitude: float, http_client: httpx.AsyncClient = None
) -> Tuple[str, Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error(get_api_message("google_maps_api_key_error"))
        return get_api_message("address_not_available"), {}

    should_close_client = False
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True

    try:
        params = {
            "latlng": f"{latitude},{longitude}",
            "key": api_key,
            "language": "en",
        }

        response = await http_client.get(GEOCODING_URL, params=params)

        if response.status_code == 200:
            data = response.json()
            if data["status"] == "OK" and data["results"]:
                result = data["results"][0]
                formatted_address = result["formatted_address"]

                # Extract components
                address_components = {}
                for component in result["address_components"]:
                    for type in component["types"]:
                        address_components[type] = component["long_name"]

                # Create structured address
                structured_address = {
                    "street": address_components.get(
                        "route", get_api_message("address_not_specified")
                    ),
                    "house": address_components.get("street_number", ""),
                    "postcode": address_components.get("postal_code", ""),
                    "city": address_components.get("locality")
                    or address_components.get("administrative_area_level_2", ""),
                    "state": address_components.get("administrative_area_level_1", ""),
                    "country": address_components.get("country", ""),
                }

                return formatted_address, {"address": structured_address}

            logger.warning(f"Geocoding API returned no results: {data}")
            return get_api_message("address_not_available"), {}

        logger.error(
            f"Geocoding API error: {response.status_code} - {response.text[:200]}"
        )
        return get_api_message("address_not_available"), {}

    except Exception as e:
        logger.error(f"Error in Geocoding API: {str(e)}", exc_info=True)
        return get_api_message("address_not_available"), {}

    finally:
        if should_close_client:
            await http_client.aclose()


async def get_walking_directions_polyline(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    http_client: httpx.AsyncClient = None,
) -> str | None:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error(get_api_message("google_maps_api_key_error"))
        return None

    should_close_client = False
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True

    try:
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{destination_lat},{destination_lng}",
            "mode": "walking",
            "key": api_key,
        }

        response = await http_client.get(DIRECTIONS_API_URL, params=params)

        if response.status_code == 200:
            data = response.json()
            if data["status"] == "OK" and data["routes"]:
                return data["routes"][0]["overview_polyline"]["points"]

            logger.warning(f"Directions API returned no results: {data}")
            return None

        logger.error(
            f"Directions API error: {response.status_code} - {response.text[:200]}"
        )
        return None

    except Exception as e:
        logger.error(f"Error in Directions API: {str(e)}", exc_info=True)
        return None

    finally:
        if should_close_client:
            await http_client.aclose()


async def get_place_photo(
    photo_reference: str, max_width: int = 600, http_client: httpx.AsyncClient = None
) -> bytes:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error(get_api_message("google_maps_api_key_error"))
        return None

    should_close_client = False
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True

    try:
        params = {
            "photo_reference": photo_reference,
            "maxwidth": str(max_width),
            "key": api_key,
        }

        response = await http_client.get(
            "https://maps.googleapis.com/maps/api/place/photo", params=params
        )

        if response.status_code == 200:
            return response.content

        logger.error(
            f"Place Photos API error: {response.status_code} - {response.text[:200]}"
        )
        return None

    except Exception as e:
        logger.error(f"Error in Place Photos API: {str(e)}", exc_info=True)
        return None

    finally:
        if should_close_client:
            await http_client.aclose()


async def test_connection():
    """Test connection to Google Maps API."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error(get_api_message("google_maps_api_key_error"))
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test geocoding API
            params = {
                "latlng": "40.714224,-73.961452",  # Example coordinates
                "key": api_key,
            }
            response = await client.get(GEOCODING_URL, params=params)
            return response.status_code == 200

    except Exception as e:
        logger.error(f"Error testing Google Maps API connection: {str(e)}")
        return False
