"""P2P Market handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "p2p_market")
async def p2p_market_menu(query: CallbackQuery):
    """
    P2P Market menu - placeholder for future feature.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                "📊 **P2P Маркет**\n\n"
                "🚧 Функция в разработке!\n\n"
                "🔜 **Скоро здесь появится:**\n"
                "• 📊 Торговля медведями между игроками\n"
                "• 💰 Выставление своих медведей на продажу\n"
                "• 🛍️ Покупка редких медведей у других игроков\n"
                "• 📊 Рыночные цены на медведей\n"
                "• 💸 Безопасные сделки с гарантией\n"
                "• 📈 История сделок\n"
                "• 🏆 Рейтинг продавцов\n\n"
                "👀 **Как это будет работать:**\n"
                "1. Выставьте своего медведя на продажу\n"
                "2. Укажите цену в коинах\n"
                "3. Другие игроки увидят ваше предложение\n"
                "4. При покупке - медведь автоматически переходит к покупателю\n\n"
                f"💼 **Ваш баланс:** {user.coins:,.0f} коинов\n\n"
                "👍 Следите за обновлениями!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔔 Уведомить о запуске", callback_data="notify_p2p")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in p2p_market_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "notify_p2p")
async def notify_p2p_launch(query: CallbackQuery):
    """
    Notify user when P2P market launches.
    """
    try:
        # TODO: Add user to notification list in database
        await query.answer(
            "✅ Вы будете уведомлены о запуске P2P маркета!",
            show_alert=True
        )
    except Exception as e:
        logger.error(f"❌ Error in notify_p2p_launch: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
