"""
Shared state and constants for handlers.
"""

from typing import Dict, Any

# Create main router
from aiogram import Router

router = Router()

# Store user data
user_data: Dict[int, Dict[str, Any]] = {}

# Store active DeepSeek requests to prevent duplicates
active_deepseek_requests: Dict[str, Dict[str, Any]] = {}

# Store user POI preferences
user_preferences: Dict[int, Dict[str, bool]] = {}

# Define POI category mappings
POI_CATEGORY_MAPPING = {
    "nature": ["park", "amusement_park", "aquarium", "campground", "zoo"],
    "religion": ["church", "hindu_temple", "mosque", "synagogue"],
    "culture": ["art_gallery"],
    "history": ["museum", "tourist_attraction"],
    "must_visit": ["point_of_interest", "tourist_attraction"],
}
