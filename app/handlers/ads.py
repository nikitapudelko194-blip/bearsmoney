"""In-game advertising handlers."""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

# Ad rewards
AD_REWARD = 100  # 100 coins per ad
AD_DAILY_LIMIT = 10  # 10 ads per day


@router.callback_query(F.data == "ads")
async def ads_menu(query: CallbackQuery):
    """Show ads menu."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Count today's views
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            views_query = select(CoinTransaction).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'ad_reward',
                CoinTransaction.created_at >= today_start
            )
            views_result = await session.execute(views_query)
            today_views = len(views_result.scalars().all())
            
            remaining = max(0, AD_DAILY_LIMIT - today_views)
            
            text = (
                f"📺 **Реклама и бонусы**\n\n"
                f"💰 За просмотр: {AD_REWARD} Coins\n"
                f"📊 Сегодня просмотрено: {today_views}/{AD_DAILY_LIMIT}\n"
                f"✨ Осталось: {remaining}\n\n"
            )
            
            if remaining > 0:
                text += f"🎬 Нажмите кнопку ниже, чтобы посмотреть рекламу!\n\n"
                text += f"💡 Смотрите до {AD_DAILY_LIMIT} видео в день и зарабатывайте!"
            else:
                text += f"⏰ Лимит исчерпан! Приходите завтра."
            
            keyboard = []
            if remaining > 0:
                keyboard.append([InlineKeyboardButton(text=f"🎬 Смотреть рекламу (+{AD_REWARD})", callback_data="ads_watch")])
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"Error in ads_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "ads_watch")
async def ads_watch(query: CallbackQuery):
    """Watch ad and get reward."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check limit
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            views_query = select(CoinTransaction).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'ad_reward',
                CoinTransaction.created_at >= today_start
            )
            views_result = await session.execute(views_query)
            today_views = len(views_result.scalars().all())
            
            if today_views >= AD_DAILY_LIMIT:
                await query.answer("⏰ Лимит просмотров исчерпан!", show_alert=True)
                return
            
            # Give reward
            user.coins += AD_REWARD
            
            transaction = CoinTransaction(
                user_id=user.id,
                amount=AD_REWARD,
                transaction_type='ad_reward',
                description='Просмотр рекламы'
            )
            session.add(transaction)
            await session.commit()
            
            remaining = AD_DAILY_LIMIT - today_views - 1
            
            text = (
                f"✅ **Награда получена!**\n\n"
                f"💰 +{AD_REWARD} Coins\n"
                f"💼 Баланс: {user.coins:,.0f} Coins\n\n"
                f"📊 Осталось просмотров: {remaining}/{AD_DAILY_LIMIT}"
            )
            
            keyboard = []
            if remaining > 0:
                keyboard.append([InlineKeyboardButton(text="🎬 Смотреть ещё", callback_data="ads_watch")])
            keyboard.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="ads")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer("🎉 Награда начислена!")
            logger.info(f"User {user.telegram_id} watched ad, earned {AD_REWARD} coins")
    except Exception as e:
        logger.error(f"Error in ads_watch: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
