"""Persistent menu keyboard."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_persistent_menu() -> ReplyKeyboardMarkup:
    """
    Get persistent menu keyboard that's always visible.
    
    Returns:
        ReplyKeyboardMarkup with main menu button
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard
