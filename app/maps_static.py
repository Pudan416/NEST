import os
import urllib.parse
from typing import List, Dict, Any
from app import logger

def create_static_map_url(
    places: List[Dict[str, Any]], 
    user_lat: float,
    user_lng: float,
    zoom: int = 13,
    size: str = "600x300",
    map_type: str = "roadmap",
    scale: int = 2
) -> str:
    """
    Create Google Maps Static API URL with numbered markers for places and user location.
    
    Args:
        places: List of place objects with position info
        user_lat: User's latitude
        user_lng: User's longitude
        zoom: Map zoom level (1-20)
        size: Map size in pixels (width x height)
        map_type: Map type (roadmap, satellite, terrain, hybrid)
        scale: Image scale for higher resolution (1 or 2)
        
    Returns:
        URL for the static map image
    """
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY is not set in environment variables")
        return None
    
    if not places:
        logger.error("No places provided for static map")
        return None
    
    # Use custom marker labels (numbers)
    markers = []
    
    # Available colors for markers
    colors = ["red", "blue", "green", "purple", "orange", "yellow", "gray", "brown", "black", "white"]
    
    for i, place in enumerate(places):
        marker_label = str(i + 1)
        marker_color = colors[i % len(colors)]
        
        lat = place["position"]["lat"]
        lng = place["position"]["lng"]
        
        marker_param = f"color:{marker_color}|label:{marker_label}|{lat},{lng}"
        markers.append(marker_param)
    
    # Add user location marker - using a special marker for user position
    user_marker = f"icon:https://maps.google.com/mapfiles/ms/icons/blue-dot.png|{user_lat},{user_lng}"
    markers.append(user_marker)
    
    # Calculate center point that includes all markers
    all_lats = [place["position"]["lat"] for place in places] + [user_lat]
    all_lngs = [place["position"]["lng"] for place in places] + [user_lng]
    
    center_lat = sum(all_lats) / len(all_lats)
    center_lng = sum(all_lngs) / len(all_lngs)
    
    # Build the API URL
    base_url = "https://maps.googleapis.com/maps/api/staticmap?"
    params = {
        "center": f"{center_lat},{center_lng}",
        "zoom": str(zoom),
        "size": size,
        "maptype": map_type,
        "scale": str(scale),
        "key": api_key,
    }
    
    url = base_url + urllib.parse.urlencode(params)
    
    # Add markers to the URL
    for marker in markers:
        url += f"&markers={urllib.parse.quote(marker)}"
    
    logger.debug(f"Generated Static Map URL (truncated): {url[:100]}...")
    return url


async def get_static_map_image(
    places: List[Dict[str, Any]], 
    user_lat: float, 
    user_lng: float,
    http_client = None
) -> bytes:
    """
    Fetch the static map image data using the Google Maps Static API.
    
    Args:
        places: List of place objects with position info
        user_lat: User's latitude
        user_lng: User's longitude
        http_client: Existing HTTP client instance
        
    Returns:
        Image data as bytes or None if failed
    """
    import httpx
    
    should_close_client = False
    
    if not http_client:
        http_client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True
    
    try:
        # Calculate appropriate zoom level based on distance
        # between user and furthest place
        from geopy.distance import geodesic
        
        max_distance = 0
        for place in places:
            place_lat = place["position"]["lat"]
            place_lng = place["position"]["lng"]
            
            distance = geodesic(
                (user_lat, user_lng),
                (place_lat, place_lng)
            ).kilometers
            
            max_distance = max(max_distance, distance)
        
        # Adjust zoom level based on maximum distance
        zoom = 14  # Default zoom level
        
        if max_distance < 0.5:
            zoom = 15
        elif max_distance < 1:
            zoom = 14
        elif max_distance < 2:
            zoom = 13
        elif max_distance < 5:
            zoom = 12
        elif max_distance < 10:
            zoom = 11
        else:
            zoom = 10
        
        # Create map URL with user location included
        map_url = create_static_map_url(
            places=places,
            user_lat=user_lat,
            user_lng=user_lng,
            zoom=zoom
        )
        
        if not map_url:
            return None
        
        # Fetch the image
        response = await http_client.get(map_url)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Failed to get static map: {response.status_code} - {response.text[:100]}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching static map: {str(e)}", exc_info=True)
        return None
    finally:
        if should_close_client:
            await http_client.aclose()