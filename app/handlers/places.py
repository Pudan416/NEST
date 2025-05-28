"""
Place preferences and settings handlers.
"""

from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.languages import get_message, get_user_language
from app import logger
from .state import router, user_preferences
from .common import create_place_types_keyboard


@router.message(Command("places"))
async def handle_places_command(message: Message):
    """Handle the /places command to set place preferences."""
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    logger.info(f"Received '/places' command from user: {user_id}")

    if user_id not in user_preferences:
        user_preferences[user_id] = {
            "nature": True,
            "religion": True,
            "culture": True,
            "history": True,
            "must_visit": True,
        }

    keyboard = create_place_types_keyboard(user_id, lang)
    await message.answer(
        get_message("choose_poi_types", lang),
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("toggle_"))
async def handle_toggle_preference(callback: CallbackQuery):
    """Handle toggling of place type preferences."""
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    pref_type = callback.data.split("_")[1]

    if user_id not in user_preferences:
        user_preferences[user_id] = {
            "nature": True,
            "religion": True,
            "culture": True,
            "history": True,
            "must_visit": True,
        }

    user_preferences[user_id][pref_type] = not user_preferences[user_id][pref_type]
    keyboard = create_place_types_keyboard(user_id, lang)

    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception as e:
        logger.debug(f"Error editing reply markup, probably not modified: {e}")
    await callback.answer()


@router.callback_query(F.data == "save_settings")
async def handle_save_settings(callback: CallbackQuery):
    """Handle saving of place type preferences."""
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    prefs = user_preferences.get(user_id, {})
    selected = [get_message(cat, lang) for cat, enabled in prefs.items() if enabled]

    if not selected:
        await callback.message.edit_text(get_message("settings_saved_none", lang))
    else:
        categories = ", ".join(selected)
        await callback.message.edit_text(
            get_message("settings_saved_with_prefs", lang).format(categories=categories)
        )
    await callback.answer()
