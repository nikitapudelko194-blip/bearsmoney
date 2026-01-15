"""Main menu keyboard for the bot."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu() -> InlineKeyboardMarkup:
    """
    Get main menu keyboard.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Row 1 - Core gameplay
        [
            InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears"),
            InlineKeyboardButton(text="🛍️ Магазин", callback_data="shop"),
        ],
        # Row 2 - Activities
        [
            InlineKeyboardButton(text="🎁 Ящики", callback_data="cases"),
            InlineKeyboardButton(text="📊 P2P Маркет", callback_data="p2p_market"),
            InlineKeyboardButton(text="📋 Квесты", callback_data="quests"),
        ],
        # Row 3 - Finance
        [
            InlineKeyboardButton(text="💱 Обмен", callback_data="exchange"),
            InlineKeyboardButton(text="💸 Вывод", callback_data="withdraw"),
        ],
        # Row 4 - Social & Stats
        [
            InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
            InlineKeyboardButton(text="📈 Статистика", callback_data="stats"),
        ],
        # Row 5 - Account
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
        ],
    ])
    return keyboard


def get_back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """
    Get back button keyboard.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)],
    ])
    return keyboard


def get_back_confirm_buttons(confirm_callback: str, cancel_callback: str = "main_menu") -> InlineKeyboardMarkup:
    """
    Get confirm/cancel buttons keyboard.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_callback),
            InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback),
        ],
    ])
    return keyboard
