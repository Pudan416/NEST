"""
Google Maps API integration for the Tourist Guide Bot.
Using only the new Places API (v1).
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple
import httpx
from app import logger

# Constants for API endpoints (Places API New)
PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"  # Geocoding API endpoint remains the same

# Supported place types in the new Places API
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
    """
    Search places by text query using Google Maps Places Text Search API.

    Args:
        query: Text to search for (e.g., "museums in Belgrade")
        http_client: Optional HTTP client for reuse

    Returns:
        List of places matching the query
    """
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
                    # Determine type from types array
                    place_type = "tourist_attraction"  # Default type
                    if place.get("types") and len(place.get("types")) > 0:
                        for t in place.get("types"):
                            if t in SUPPORTED_PLACE_TYPES:
                                place_type = t
                                break
                    
                    # Format place data
                    formatted_place = {
                        "id": place.get("id"),
                        "title": place.get("displayName", {}).get("text", "Unknown Place"),
                        "type": place_type,
                        "position": {
                            "lat": place.get("location", {}).get("latitude", 0),
                            "lng": place.get("location", {}).get("longitude", 0),
                        },
                        "address": {
                            "label": place.get("formattedAddress", "Address will be fetched")
                        },
                        "contacts": [
                            {"www": place.get("websiteUri", "url_not_found")}
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
    """
    Fetch nearby tourist destinations using Google Maps Places API.

    Args:
        latitude: The latitude coordinate
        longitude: The longitude coordinate
        radius: Search radius in meters (max 50000)
        place_types: List of place types to search for (e.g., ["museum", "tourist_attraction"])
        http_client: Optional HTTP client for reuse

    Returns:
        List of places with details
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return []

    # Default place types if none provided
    if not place_types:
        place_types = SUPPORTED_PLACE_TYPES
    else:
        # Filter to include only supported types
        place_types = [t for t in place_types if t in SUPPORTED_PLACE_TYPES]
        if not place_types:
            logger.warning("No supported place types found in the requested types")
            place_types = ["tourist_attraction", "museum"]  # Fallback to common types

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
        
        # Create combined results from all place types
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
                        # Format to match your existing format
                        formatted_place = {
                            "id": place.get("id"),
                            "title": place.get("displayName", {}).get("text", "Unknown Place"),
                            "type": place_type,
                            "position": {
                                "lat": place.get("location", {}).get("latitude", 0),
                                "lng": place.get("location", {}).get("longitude", 0),
                            },
                            "address": {
                                "label": place.get("formattedAddress", "Address will be fetched")
                            },
                            "contacts": [
                                {"www": place.get("websiteUri", "url_not_found")}
                            ],
                        }
                        
                        # Add to places list if not a duplicate
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
    """
    Get detailed information about a specific place.

    Args:
        place_id: Google Place ID
        http_client: Optional HTTP client for reuse

    Returns:
        Dictionary containing place details
    """
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
        # Include photos in the field mask
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
            
            # Format the details in a standardized structure
            details = {
                "name": place_data.get("displayName", {}).get("text", "Unknown Place"),
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
                "photos": []  # Initialize photos array
            }
            
            # Process photos if available
            if "photos" in place_data and place_data["photos"]:
                photo_references = []
                for photo in place_data["photos"]:
                    if "name" in photo:
                        photo_references.append(photo["name"])
                
                # Store photo references for later use
                details["photo_references"] = photo_references
                
                # Get first photo if available
                if photo_references:
                    # Format photo URL to get an image
                    # We'll use the first photo reference
                    details["main_photo_reference"] = photo_references[0]
            
            # Process opening hours
            if place_data.get("regularOpeningHours", {}).get("periods"):
                for period in place_data["regularOpeningHours"]["periods"]:
                    if "open" in period and "day" in period["open"]:
                        day = period["open"]["day"]
                        
                        # Fix type conversion issue - ensure hour and minute are strings
                        open_hour = period["open"].get("hour", "00")
                        open_minute = period["open"].get("minute", "00")
                        # Convert to strings if they're integers
                        if isinstance(open_hour, int):
                            open_hour = str(open_hour).zfill(2)
                        if isinstance(open_minute, int):
                            open_minute = str(open_minute).zfill(2)
                        
                        open_time = f"{open_hour}:{open_minute}"
                        
                        close_time = "24:00"
                        if "close" in period:
                            # Same fix for close times
                            close_hour = period["close"].get("hour", "00")
                            close_minute = period["close"].get("minute", "00")
                            # Convert to strings if they're integers
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
    """
    Get a detailed address using Google Maps Geocoding API.

    Args:
        latitude: The latitude coordinate
        longitude: The longitude coordinate
        http_client: Optional HTTP client for reuse

    Returns:
        Tuple containing (formatted_address, full_response_data)
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return "Address not available", {}

    try:
        params = {
            "latlng": f"{latitude},{longitude}",
            "key": api_key,
            "language": "en",  # Get results in English
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
                    # Get the first result (most accurate)
                    result = data["results"][0]
                    formatted_address = result.get(
                        "formatted_address", "Address not available"
                    )

                    # Extract address components
                    address_components = {}
                    for component in result.get("address_components", []):
                        types = component.get("types", [])
                        
                        # Map common address components
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

                    # Return formatted address and detailed data
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

    return "Address not available", {}

async def get_place_photo(
    photo_reference: str, max_width: int = 600, http_client: httpx.AsyncClient = None
) -> bytes:
    """
    Get a photo of a place using the photo reference from Place Details.
    
    Args:
        photo_reference: The photo reference string from Place Details
        max_width: Maximum width of the photo
        http_client: Optional HTTP client for reuse
        
    Returns:
        Photo data as bytes or None if photo cannot be retrieved
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return None
        
    should_close_client = False
    
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)  # <-- Enable follow_redirects
        should_close_client = True
    
    try:
        logger.debug(f"Getting place photo for reference: {photo_reference}")
        
        # Check if reference is valid
        if not photo_reference or not isinstance(photo_reference, str):
            logger.error(f"Invalid photo reference: {photo_reference}")
            return None
            
        # Construct the URL for the photo
        url = f"https://places.googleapis.com/v1/{photo_reference}/media"
        
        headers = {
            "X-Goog-Api-Key": api_key,
            "Accept": "image/*"
        }
        
        # Add maxWidthPx parameter
        params = {
            "maxWidthPx": max_width
        }
        
        logger.debug(f"Place Photo API request: URL={url}, Headers={headers}, Params={params}")
        
        # Make a request with automatic redirection enabled
        response = await http_client.get(
            url,
            headers=headers,
            params=params,
            follow_redirects=True  # <-- Make sure redirects are followed
        )
        
        logger.debug(f"Response status: {response.status_code}, Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            logger.debug(f"Successfully retrieved photo, size: {len(response.content)} bytes")
            
            # Make sure we actually got an image
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('image/'):
                return response.content
            else:
                logger.error(f"Received non-image content type: {content_type}")
                # Log first 100 bytes to see what we received
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
    """Test the connection to Google Maps APIs."""
    try:
        # Test nearby search with a known location (e.g., Belgrade city center)
        test_lat, test_lng = 44.802416, 20.465601
        
        http_client = httpx.AsyncClient(timeout=30.0)
        
        try:
            # Test text search
            logger.info("Testing Places API Text Search...")
            text_places = await search_places_by_text("Belgrade attractions", http_client)
            if text_places:
                text_result = f"✅ Places API text search: Found {len(text_places)} places"
            else:
                text_result = "❌ Places API text search: No places found"
            
            # Test nearby search
            logger.info("Testing Places API Nearby Search...")
            nearby_places = await get_nearby_places(
                test_lat, test_lng, radius=500, 
                place_types=["tourist_attraction", "museum"], 
                http_client=http_client
            )
            
            if nearby_places:
                nearby_result = f"✅ Nearby search: Found {len(nearby_places)} places near test coordinates"
                
                # Test place details for the first place
                if nearby_places[0].get("id"):
                    logger.info(f"Testing Places API Details for place: {nearby_places[0]['id']}...")
                    place_details = await get_place_details(
                        nearby_places[0]["id"], http_client=http_client
                    )
                    if place_details:
                        details_result = "✅ Successfully retrieved place details"
                    else:
                        details_result = "❌ Failed to retrieve place details"
                else:
                    details_result = "❌ No place ID available to test details"
            else:
                nearby_result = "❌ No places found near test coordinates"
                details_result = "❌ Skipped place details test"
                
            # Test geocoding
            logger.info("Testing Geocoding API...")
            address, address_data = await get_detailed_address(
                test_lat, test_lng, http_client=http_client
            )
            if address != "Address not available":
                geocoding_result = f"✅ Geocoding successful: {address}"
            else:
                geocoding_result = "❌ Geocoding failed"
                
            return f"""
Google Maps API Connection Test Results:
---------------------------------------
1. {text_result}
2. {nearby_result}
3. {details_result}
4. {geocoding_result}

Test location: Belgrade city center ({test_lat}, {test_lng})
            """
        finally:
            await http_client.aclose()
    except Exception as e:
        return f"❌ API test failed: {str(e)}"