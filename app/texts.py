MESSAGES = {
    # Start command message
    'start': "🐦 Coo-coo-COOO! \n\n"
             "Welcome to NEST - Navigate, Explore, See, Travel!\n"
             "I am Nesty, a pigeon-expert of whatever concrete jungles you are in.\n\n"
             "📍 Drop your location and I'll find the best nearby spots worth your attention!\n\n"
             "Let's spread our wings and explore together!",
    
    # Error messages
    'error': "An error occurred. Please try again later.",
    'try_again': "🐦 Squawk! Please try again later.",
    'error_showing_place': "🐦 Squawk! There was an error showing this place. Please try again.",
    'error_next_place': "🐦 Squawk! There was an error showing the next place. Please try again.",
    'forgot_to_say': "🐦 Squawk! I forgot what I was going to say. Please try again.",
    
    # Location search messages
    'scouting': "🐦 Taking off to scout the area!",
    'searching_wider': "🐦 Found a few spots nearby, but searching wider for more options...",
    'searching_farthest': "🐦 Just a few more seconds while I search farther away...",
    'no_places': "🐦 Well... Even us city birds don't hang around here much. Try dropping your pin somewhere else!",
    'places_found': "🐦 Spotted {count} cool spots nearby! Swooping down to check them out...",
    'lost_track': "🐦 Sorry, I lost track of our journey! Can you share your location again?",
    'lost_track_alert': "I lost track of our journey! Please share your location again.",
    'reading_signs': "🐦 Reading the signposts and street names...",
    'need_location': "🐦 I need coordinates to fly to, friend! Share your location or coo '/start' to begin our urban adventure!",
    
    # Button text
    'tell_more_btn': "💬 Tell me more",
    'show_maps_btn': "🗺️ Show on Google Maps",
    'next_location': "➡️ Next location",
    'back_to_first': "🔄 Back to first",
    
    # More information request messages
    'request_in_progress': "I'm still thinking about this place! Please wait a moment...",
    'cooldown': "I just told you about this place! Try again in {seconds} seconds.",
    'gathering_thoughts': "Let me gather my thoughts about this place...",
    'checking_details': "🐦 Wait, let me check the details first...",
    'remembered_place': "🐦 I remember telling you about this place...",
    'digging_memories': "🐦 Digging into my memories about this place...",
    'about_place': "<b>About {place_name}</b>\n\n<blockquote expandable>{history}</blockquote>",
    'audio_too_large': "The audio message is too large to send.",
    'voice_tired': "🐦 My vocal cords are tired from all this cooing! Try again when my voice recovers!"
}

# API-related messages
API_MESSAGES = {
    # DeepSeek API error messages
    'deepseek_api_key_error': "Error: DeepSeek API key is not configured. Please check your environment variables.",
    'invalid_api_key': "Error: Invalid API key. Please check your API credentials.",
    'rate_limit_exceeded': "Error: Rate limit exceeded. Please try again later.",
    'no_content': "No content found in response.",
    'unexpected_format': "Error: Unexpected response format.",
    'connection_timeout': "Error: Connection timeout. The API service might be unavailable.",
    'read_timeout': "Error: Read timeout. The request took too long to process.",
    'multiple_failures': "Error: Failed after multiple attempts to contact DeepSeek API.",
    
    # Address-related messages
    'address_not_available': "Address not available", 
    'address_not_specified': "Address not specified",
    
    # DeepSeek prompts
    'deepseek_test_prompt': "Hello, are you working?",
    'translator_system_prompt': "You are a professional translator. Translate the given text to English. Preserve proper nouns but translate everything else. Keep the translation concise and accurate. Only respond with the translation, nothing else.",
    'translate_prompt': "Translate this to English: {text}",
    
    # Location info messages
    'insufficient_info': "Unable to generate a story due to insufficient information.",
    'location_system_prompt': "You are a time traveller that has seen the past and knows everything about the {city}. "
                             "Provide a concise historical overview of {poi_name}, located at {poi_address}. {context}"
                             "Structure your response as follows: First make a short yet catchy explanation of the place, that teases what you will talk about later. "
                             "Then follow this structure in your response: describe its appearance and key features; then tell proven historical facts about the place (if they exist), "
                             "Keep the response under 150 words, engaging, and informative. Use your imagination and creativity to bring the story to life. "
                             "Use only English language throughout the entire response.",
    'location_user_prompt': "Street: {street}, City: {city}, POI: {poi_name}, Address: {poi_address}"
}

# Google Maps specific messages
GOOGLE_MAPS_MESSAGES = {
    # Place information
    'unknown_place': "Unknown Place",
    'address_fetch': "Address will be fetched",
    'url_not_found': "url_not_found",
    'address_not_available': "Address not available",
    
    # Test connection messages
    'test_query': "Belgrade attractions",
    'text_search_success': "✅ Places API text search: Found {count} places",
    'text_search_failure': "❌ Places API text search: No places found",
    'nearby_search_success': "✅ Nearby search: Found {count} places near test coordinates",
    'nearby_search_failure': "❌ No places found near test coordinates",
    'details_success': "✅ Successfully retrieved place details",
    'details_failure': "❌ Failed to retrieve place details",
    'no_place_id': "❌ No place ID available to test details",
    'details_skipped': "❌ Skipped place details test",
    'geocoding_success': "✅ Geocoding successful: {address}",
    'geocoding_failure': "❌ Geocoding failed",
    'test_failed': "❌ API test failed: {error}",
    
    # Test results template
    'test_results': """
Google Maps API Connection Test Results:
---------------------------------------
1. {text_result}
2. {nearby_result}
3. {details_result}
4. {geocoding_result}

Test location: Belgrade city center ({test_lat}, {test_lng})
            """
}