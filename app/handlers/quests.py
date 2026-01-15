"""Quests handler."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "quests")
async def quests_menu(query: CallbackQuery):
    """
    Show quests menu (placeholder).
    """
    try:
        text = (
            "📋 **Квесты**\n\n"
            "🕒 Функция в разработке...\n\n"
            "✨ **Скоро будет доступно:**\n"
            "- 🎯 Ежедневные квесты\n"
            "- 🏆 Недельные задания\n"
            "- 🎁 Специальные события\n"
            "- 💰 Щедрые награды\n\n"
            "🔔 Оставайтесь на связи!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in quests_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
