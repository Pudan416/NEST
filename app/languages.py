"""
Language management module for the Tourist Guide Bot.
Handles translations, language preferences, and message templates.
"""

from typing import Dict, Any

# Core configuration
DEFAULT_LANGUAGE = "ru"
AVAILABLE_LANGUAGES = {"ru": "🇷🇺 Привет!", "en": "🇬🇧 Hello!"}

# User preferences storage
user_languages: Dict[int, str] = {}

# Common message components
EMOJI_MAP = {
    "nature": "🏞️",
    "religion": "⛪",
    "culture": "🎭",
    "history": "🏛️",
    "must_visit": "⭐",
    "save": "💾",
    "bird": "🐦",
    "pin": "📍",
    "map": "🗺️",
    "chat": "💬",
    "next": "➡️",
    "reload": "🔄",
}

# Base messages that don't need translation
BASE_MESSAGES = {
    "deepseek_api_key_error": "Error: DeepSeek API key is not configured. Please check your environment variables.",
    "invalid_api_key": "Error: Invalid API key. Please check your API credentials.",
    "rate_limit_exceeded": "Error: Rate limit exceeded. Please try again later.",
    "no_content": "No content found in response.",
    "unexpected_format": "Error: Unexpected response format.",
    "connection_timeout": "Error: Connection timeout. The API service might be unavailable.",
    "read_timeout": "Error: Read timeout. The request took too long to process.",
    "multiple_failures": "Error: Failed after multiple attempts to contact DeepSeek API.",
    "address_not_available": "Address not available",
    "address_not_specified": "Address not specified",
    "yandex_api_key_error": "Error: Yandex SpeechKit API key is not configured. Please check your environment variables.",
    "yandex_tts_error": "Error: Failed to generate speech. Please try again later.",
    "google_maps_api_key_error": "Error: Google Maps API key is not configured. Please check your environment variables.",
    "unknown_place": "Unknown Place",
    "address_fetch": "Address will be fetched",
    "url_not_found": "url_not_found",
    "google_maps_error": "Error accessing Google Maps API. Please try again later.",
}

# API-specific prompts
API_PROMPTS = {
    "deepseek_test_prompt": "Hello, are you working?",
    "translator_system_prompt": """You are a professional translator. Translate the given text to English. 
Preserve proper nouns but translate everything else. Keep the translation concise and accurate. 
Only respond with the translation, nothing else.""",
    "translate_prompt": "Translate this to English: {text}",
    "location_system_prompt_en": """You are a time traveller that has seen the past and knows everything about the {city}. 
Provide a concise historical overview of {poi_name}, located at {poi_address}. {context}
Structure your response as follows: First make a short yet catchy explanation of the place, that teases what you will talk about later. 
Then follow this structure in your response: describe its appearance and key features; then tell proven historical facts about the place (if they exist).
Keep the response under 150 words, engaging, and informative. Use your imagination and creativity to bring the story to life. 
Use only English language throughout the entire response.""",
    "location_system_prompt_ru": """Вы путешественник во времени, который видел прошлое и знает всё о городе {city}. 
Предоставьте краткий исторический обзор места {poi_name}, расположенного по адресу {poi_address}. {context}
Структурируйте ваш ответ следующим образом: Сначала сделайте короткое, но интригующее объяснение места, которое заинтересует читателя. 
Затем следуйте этой структуре: опишите его внешний вид и ключевые особенности; расскажите проверенные исторические факты об этом месте (если они есть). 
Ограничьте ответ 150 словами, сделайте его увлекательным и информативным. Используйте воображение и творческий подход, чтобы оживить историю. 
Используйте только русский язык на протяжении всего ответа.""",
    "location_user_prompt": "Street: {street}, City: {city}, POI: {poi_name}, Address: {poi_address}",
}

# Translated messages
MESSAGES = {
    "en": {
        "start": f"{EMOJI_MAP['bird']} Coo-coo-COOO! \n\n"
        "Welcome to NEST - Navigate, Explore, See, Travel!\n"
        "I am Nesty, a pigeon-expert of whatever concrete jungles you are in.\n\n"
        f"{EMOJI_MAP['pin']} Drop your location and I'll find the best nearby spots worth your attention!\n\n"
        "Let's spread our wings and explore together!",
        "error": "An error occurred. Please try again later.",
        "try_again": f"{EMOJI_MAP['bird']} Squawk! Please try again later.",
        "error_showing_place": f"{EMOJI_MAP['bird']} Squawk! There was an error showing this place. Please try again.",
        "error_next_place": f"{EMOJI_MAP['bird']} Squawk! There was an error showing the next place. Please try again.",
        "forgot_to_say": f"{EMOJI_MAP['bird']} Squawk! I forgot what I was going to say. Please try again.",
        "scouting": f"{EMOJI_MAP['bird']} Taking off to scout the area!",
        "searching_wider": f"{EMOJI_MAP['bird']} Found a few spots nearby, but searching wider for more options...",
        "searching_farthest": f"{EMOJI_MAP['bird']} Just a few more seconds while I search farther away...",
        "generating_map": f"{EMOJI_MAP['bird']} Creating a map of all the spots I found...",
        "no_places": f"{EMOJI_MAP['bird']} Well... Even us city birds don't hang around here much. Try dropping your pin somewhere else!",
        "places_found": f"{EMOJI_MAP['bird']} Spotted {{count}} cool spots nearby! Swooping down to check them out...",
        "lost_track": f"{EMOJI_MAP['bird']} Sorry, I lost track of our journey! Can you share your location again?",
        "lost_track_alert": "I lost track of our journey! Please share your location again.",
        "reading_signs": f"{EMOJI_MAP['bird']} Reading the signposts and street names...",
        "need_location": f"{EMOJI_MAP['bird']} I need coordinates to fly to, friend! Share your location or coo '/start' to begin our urban adventure!",
        "map_caption": f"{EMOJI_MAP['map']} Map showing all {{count}} locations near you. The numbers show each location, and the {EMOJI_MAP['pin']} shows your position.",
        "tell_more_btn": f"{EMOJI_MAP['chat']} Tell me more",
        "show_maps_btn": f"{EMOJI_MAP['map']} Show on Google Maps",
        "next_location": f"{EMOJI_MAP['next']} Next location",
        "back_to_first": f"{EMOJI_MAP['reload']} Back to first",
        "request_in_progress": "I'm still thinking about this place! Please wait a moment...",
        "cooldown": "I just told you about this place! Try again in {seconds} seconds.",
        "gathering_thoughts": "Let me gather my thoughts about this place...",
        "checking_details": f"{EMOJI_MAP['bird']} Wait, let me check the details first...",
        "remembered_place": f"{EMOJI_MAP['bird']} I remember telling you about this place...",
        "digging_memories": f"{EMOJI_MAP['bird']} Digging into my memories about this place...",
        "about_place": "<b>About {place_name}</b>\n\n<blockquote expandable>{history}</blockquote>",
        "audio_too_large": "The audio message is too large to send.",
        "voice_tired": f"{EMOJI_MAP['bird']} My vocal cords are tired from all this cooing! Try again when my voice recovers!",
        "nature": "Nature",
        "religion": "Religion",
        "culture": "Culture",
        "history": "History",
        "must_visit": "Must Visit",
        "save_and_close": "Save & Close",
        "choose_poi_types": "Choose your preferred Points of Interest types (you can select multiple):",
        "settings_saved_none": "Settings saved! No specific preferences set - I'll show you all types of places.",
        "settings_saved_with_prefs": "Settings saved! I'll focus on showing you places related to: {categories}",
        "no_places_selected": "What do you want me to search for? Choose at least some /places",
    },
    "ru": {
        "start": f"{EMOJI_MAP['bird']} Привет! \n\n"
        "Добро пожаловать в NEST!\n"
        "Я Нести, голубь-эксперт по бетонным джунглям.\n\n"
        f"{EMOJI_MAP['pin']} Отправь свою локацию, и я расскажу лучшие места поблизости, достойные твоего внимания!\n\n"
        "Расправим крылья и исследуем вместе!",
        "error": "Произошла ошибка. Пожалуйста, попробуй позже.",
        "try_again": f"{EMOJI_MAP['bird']} Курлык! Пожалуйста, попробуй позже.",
        "error_showing_place": f"{EMOJI_MAP['bird']} Курлык! Произошла ошибка при показе этого места. Пожалуйста, попробуй снова.",
        "error_next_place": f"{EMOJI_MAP['bird']} Курлык! Произошла ошибка при показе следующего места. Пожалуйста, попробуй снова.",
        "forgot_to_say": f"{EMOJI_MAP['bird']} Курлык! Я забыл, что хотел сказать. Пожалуйста, попробуй снова.",
        "scouting": f"{EMOJI_MAP['bird']} Взлетаю на разведку местности!",
        "searching_wider": f"{EMOJI_MAP['bird']} Нашел несколько мест поблизости, но ищу еще...",
        "searching_farthest": f"{EMOJI_MAP['bird']} Еще несколько секунд, пока я ищу подальше...",
        "generating_map": f"{EMOJI_MAP['bird']} Создаю карту всех найденных мест...",
        "no_places": f"{EMOJI_MAP['bird']} Ну... Даже мы, городские птицы, здесь не часто бываем. Попробуйте отметить другое место!",
        "places_found": f"{EMOJI_MAP['bird']} Обнаружил {{count}} классных мест поблизости! Спускаюсь, чтобы проверить их...",
        "lost_track": f"{EMOJI_MAP['bird']} Извините, я потерял след нашего путешествия! Можете поделиться локацией снова?",
        "lost_track_alert": "Я потерял след нашего путешествия! Пожалуйста, поделитесь локацией снова.",
        "reading_signs": f"{EMOJI_MAP['bird']} Читаю указатели и названия улиц...",
        "need_location": f"{EMOJI_MAP['bird']} Мне нужны координаты для полета, друг! Поделитесь локацией или напишите '/start', чтобы начать наше городское приключение!",
        "map_caption": f"{EMOJI_MAP['map']} Карта показывает все {{count}} мест рядом с вами. Цифры показывают каждое место, а {EMOJI_MAP['pin']} показывает вашу локацию.",
        "tell_more_btn": f"{EMOJI_MAP['chat']} Расскажи",
        "show_maps_btn": f"{EMOJI_MAP['map']} Карта",
        "next_location": f"{EMOJI_MAP['next']} Следующее место",
        "back_to_first": f"{EMOJI_MAP['reload']} Давай по новой",
        "request_in_progress": "Я все еще думаю об этом месте! Пожалуйста, подождите...",
        "cooldown": "Я только что рассказал об этом месте! Попробуйте через {seconds} секунд.",
        "gathering_thoughts": "Позвольте мне собраться с мыслями об этом месте...",
        "checking_details": f"{EMOJI_MAP['bird']} Подождите, я проверяю детали...",
        "remembered_place": f"{EMOJI_MAP['bird']} Я помню, что рассказывал вам об этом месте...",
        "digging_memories": f"{EMOJI_MAP['bird']} Копаюсь в воспоминаниях об этом месте...",
        "about_place": "<b>О месте {place_name}</b>\n\n<blockquote expandable>{history}</blockquote>",
        "audio_too_large": "Аудиосообщение слишком большое для отправки.",
        "voice_tired": f"{EMOJI_MAP['bird']} Мои голосовые связки устали от всего этого курлыканья! Попробуйте, когда мой голос восстановится!",
        "nature": "Природа",
        "religion": "Религия",
        "culture": "Культура",
        "history": "История",
        "must_visit": "Основные места",
        "save_and_close": "Сохранить и закрыть",
        "choose_poi_types": "Выберите интересующие вас типы достопримечательностей (можно выбрать несколько):",
        "settings_saved_none": "Настройки сохранены! Не выбраны конкретные предпочтения - я покажу все типы мест.",
        "settings_saved_with_prefs": "Настройки сохранены! Я сосредоточусь на местах, связанных с: {categories}",
        "no_places_selected": "Что мне искать? Выберите хотя бы несколько /places",
    },
}


def get_message(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Get a message in the specified language with fallback to default language."""
    return MESSAGES.get(lang, MESSAGES[DEFAULT_LANGUAGE]).get(
        key, MESSAGES[DEFAULT_LANGUAGE].get(key, f"Message not found: {key}")
    )


def get_api_message(key: str) -> str:
    """Get an API-related message."""
    return BASE_MESSAGES.get(key, f"API message not found: {key}")


def get_api_prompt(key: str) -> str:
    """Get an API prompt template."""
    return API_PROMPTS.get(key, f"API prompt not found: {key}")


def get_user_language(user_id: int) -> str:
    """Get user's preferred language with fallback to default."""
    return user_languages.get(user_id, DEFAULT_LANGUAGE)


def set_user_language(user_id: int, language: str) -> None:
    """Set user's preferred language if it's available."""
    if language in AVAILABLE_LANGUAGES:
        user_languages[user_id] = language
