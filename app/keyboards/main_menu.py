"""Main menu keyboard."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard.
    
    Returns:
        ReplyKeyboardMarkup: Main menu keyboard
    """
    buttons = [
        [
            KeyboardButton(text="🐻 Мои медведи"),
            KeyboardButton(text="💵 Мои коины")
        ],
        [
            KeyboardButton(text="🎪 Магазин"),
            KeyboardButton(text="💳 Кошелёк")
        ],
        [
            KeyboardButton(text="📋 Квесты"),
            KeyboardButton(text="🌟 Мой профиль")
        ],
        [
            KeyboardButton(text="🔗 Реферал"),
            KeyboardButton(text="🎈 Кейсы")
        ],
        [
            KeyboardButton(text="❓ Помощь")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_back_button() -> InlineKeyboardMarkup:
    """Get back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ]
    )
