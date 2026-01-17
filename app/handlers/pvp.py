"""PvP battles handlers."""
import logging
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Bear, CoinTransaction
from app.services.bears import BEAR_CLASSES

logger = logging.getLogger(__name__)
router = Router()

# PvP ranks
PVP_RANKS = {
    "bronze": {"name": "Bronze", "emoji": "🥉", "min_rating": 0, "max_rating": 1000},
    "silver": {"name": "Silver", "emoji": "🥈", "min_rating": 1001, "max_rating": 2000},
    "gold": {"name": "Gold", "emoji": "🥇", "min_rating": 2001, "max_rating": 3000},
    "platinum": {"name": "Platinum", "emoji": "💎", "min_rating": 3001, "max_rating": 4000},
    "diamond": {"name": "Diamond", "emoji": "💎💎", "min_rating": 4001, "max_rating": 5000},
    "legend": {"name": "Legend", "emoji": "🎯", "min_rating": 5001, "max_rating": 999999}
}

MIN_BET = 100
MAX_BET = 10000


@router.callback_query(F.data == "pvp_battles")
async def pvp_menu(query: CallbackQuery):
    """Show PvP battles menu."""
    try:
        text = (
            "⚔️ **PvP Батлы Медведей**\n\n"
            "🎯 **Как это работает:**\n"
            "1. Выберите своего медведя\n"
            "2. Сделайте ставку (100-10,000 Coins)\n"
            "3. Система найдёт соперника\n"
            "4. Победитель забирает всё!\n\n"
            "🏆 **Ранговая система:**\n"
            "🥉 Bronze (0-1000)\n"
            "🥈 Silver (1001-2000)\n"
            "🥇 Gold (2001-3000)\n"
            "💎 Platinum (3001-4000)\n"
            "💎💎 Diamond (4001-5000)\n"
            "🎯 Legend (5001+)\n\n"
            "🚧 **Функция в разработке!**"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in pvp_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
