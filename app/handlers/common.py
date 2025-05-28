"""
Common utilities and helper functions for handlers.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.languages import get_message, EMOJI_MAP
from .state import user_preferences


def create_place_types_keyboard(user_id: int, lang: str) -> InlineKeyboardMarkup:
    """Create keyboard for place type selection."""
    prefs = user_preferences.get(
        user_id,
        {
            "nature": True,
            "religion": True,
            "culture": True,
            "history": True,
            "must_visit": True,
        },
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI_MAP['nature']} {get_message('nature', lang)} {'✅' if prefs['nature'] else '◻️'}",
                    callback_data="toggle_nature",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJI_MAP['religion']} {get_message('religion', lang)} {'✅' if prefs['religion'] else '◻️'}",
                    callback_data="toggle_religion",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJI_MAP['culture']} {get_message('culture', lang)} {'✅' if prefs['culture'] else '◻️'}",
                    callback_data="toggle_culture",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJI_MAP['history']} {get_message('history', lang)} {'✅' if prefs['history'] else '◻️'}",
                    callback_data="toggle_history",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJI_MAP['must_visit']} {get_message('must_visit', lang)} {'✅' if prefs['must_visit'] else '◻️'}",
                    callback_data="toggle_must_visit",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJI_MAP['save']} {get_message('save_and_close', lang)}",
                    callback_data="save_settings",
                )
            ],
        ]
    )


def create_language_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for language selection."""
    from app.languages import AVAILABLE_LANGUAGES

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"lang_{code}")]
            for code, name in AVAILABLE_LANGUAGES.items()
        ]
    )
