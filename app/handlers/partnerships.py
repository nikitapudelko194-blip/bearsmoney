"""Partnerships and cross-promotion handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "partnerships")
async def partnerships_menu(query: CallbackQuery):
    """Show partnerships menu."""
    try:
        text = (
            "🤝 **Партнёры**\n\n"
            "🌟 Мы сотрудничаем с лучшими проектами в TON!\n\n"
            "📊 **Партнёрские предложения:**\n"
            "• Эксклюзивные кейсы\n"
            "• Специальные медведи\n"
            "• Бонусные награды\n"
            "• Кросс-промо с другими играми\n\n"
            "🚧 **Скоро:**\n"
            "• Интеграция с TON Play\n"
            "• Партнёрские турниры\n"
            "• Спонсорские события\n\n"
            "💬 **Хотите стать партнёром?**\n"
            "Напишите в поддержку: @bearsmoney_support"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in partnerships_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
