"""
Start command and language selection handlers.
"""

from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from app.languages import get_message, get_user_language, set_user_language
from app import logger
from .state import router, user_preferences
from .common import create_language_keyboard, create_place_types_keyboard


@router.message(CommandStart())
async def handle_start_command(message: Message, db=None):
    """Handle the /start command."""
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name

        logger.info(f"Received '/start' command from user: {user_id}")

        if db:
            db.add_or_update_user(user_id, username, first_name, last_name)

        # Initialize user preferences if not already set
        if message.from_user.id not in user_preferences:
            user_preferences[message.from_user.id] = {
                "nature": True,
                "religion": True,
                "culture": True,
                "history": True,
                "must_visit": True,
            }

        # Show language selection first
        keyboard = create_language_keyboard()
        await message.answer("🐦", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in '/start' command handler: {e}", exc_info=True)
        await message.answer(get_message("error", "ru"))


@router.message(Command("languages"))
async def handle_languages_command(message: Message):
    """Handle the /languages command to change language."""
    user_id = message.from_user.id
    logger.info(f"Received '/languages' command from user: {user_id}")
    keyboard = create_language_keyboard()
    await message.answer("🐦", reply_markup=keyboard)


@router.callback_query(F.data.startswith("lang_"))
async def handle_language_selection(callback: CallbackQuery):
    """Handle language selection callback."""
    user_id = callback.from_user.id
    lang = callback.data.split("_")[1]

    set_user_language(user_id, lang)
    await callback.message.edit_text(get_message("language_selected", lang))

    # After language selection, show the welcome message
    await callback.message.answer(get_message("start", lang))

    # Initialize user preferences if not already set
    if user_id not in user_preferences:
        user_preferences[user_id] = {
            "nature": True,
            "religion": True,
            "culture": True,
            "history": True,
            "must_visit": True,
        }

    # Show POI settings right after welcome message
    keyboard = create_place_types_keyboard(user_id, lang)
    await callback.message.answer(
        get_message("choose_poi_types", lang),
        reply_markup=keyboard,
    )
    await callback.answer()
