"""
Handlers package for the Tourist Guide Bot.
Contains all the message and callback handlers organized by functionality.
"""

from .state import router

# Store user data
user_data = {}
# Store active DeepSeek requests to prevent duplicates
active_deepseek_requests = {}
# Store user POI preferences
user_preferences = {}

# Define POI category mappings
POI_CATEGORY_MAPPING = {
    "nature": ["park", "amusement_park", "aquarium", "campground", "zoo"],
    "religion": ["church", "hindu_temple", "mosque", "synagogue"],
    "culture": ["art_gallery"],
    "history": ["museum", "tourist_attraction"],
    "must_visit": ["point_of_interest", "tourist_attraction"],
}

# Import all handlers
from . import start
from . import location
from . import places
from . import common
