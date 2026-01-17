"""In-game advertising handlers."""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select, func
from app.database.db import get_session
from app.database.models import User, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

# Ad rewards
AD_REWARD_COINS = 100
MAX_ADS_PER_DAY = 10


async def get_ads_watched_today(user_id: int, session) -> int:
    """Get number of ads watched today."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = select(func.count(CoinTransaction.id)).where(
        CoinTransaction.user_id == user_id,
        CoinTransaction.transaction_type == 'ad_reward',
        CoinTransaction.created_at >= today_start
    )
    result = await session.execute(query)
    return result.scalar() or 0


@router.callback_query(F.data == "watch_ad")
async def watch_ad_menu(query: CallbackQuery):
    """Show ad watching menu."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            ads_today = await get_ads_watched_today(user.id, session)
            ads_left = max(0, MAX_ADS_PER_DAY - ads_today)
            
            text = (
                "📺 **Просмотр рекламы**\n\n"
                f"💰 **Награда за просмотр:** {AD_REWARD_COINS} Coins\n"
                f"👀 **Просмотрено сегодня:** {ads_today}/{MAX_ADS_PER_DAY}\n"
                f"📊 **Осталось:** {ads_left} видео\n\n"
            )
            
            if ads_left > 0:
                text += "🎬 Нажмите кнопку ниже, чтобы посмотреть рекламу и получить награду!"
            else:
                text += "⏰ Вы достигли дневного лимита. Приходите завтра!"
            
            keyboard = []
            
            if ads_left > 0:
                keyboard.append([InlineKeyboardButton(
                    text="▶️ Смотреть рекламу",
                    callback_data="watch_ad_confirm"
                )])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in watch_ad_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "watch_ad_confirm")
async def watch_ad_confirm(query: CallbackQuery):
    """Simulate ad watching and give reward."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            ads_today = await get_ads_watched_today(user.id, session)
            
            if ads_today >= MAX_ADS_PER_DAY:
                await query.answer("⏰ Дневной лимит достигнут!", show_alert=True)
                return
            
            # Add reward
            user.coins += AD_REWARD_COINS
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=AD_REWARD_COINS,
                transaction_type='ad_reward',
                description=f'Награда за просмотр рекламы'
            )
            session.add(transaction)
            
            await session.commit()
            
            ads_left = MAX_ADS_PER_DAY - ads_today - 1
            
            text = (
                "✅ **Спасибо за просмотр!**\n\n"
                f"💰 Вы получили: {AD_REWARD_COINS} Coins\n"
                f"💼 Новый баланс: {user.coins:,.0f} Coins\n\n"
                f"📊 Осталось видео сегодня: {ads_left}\n"
            )
            
            keyboard = []
            
            if ads_left > 0:
                keyboard.append([InlineKeyboardButton(
                    text="▶️ Смотреть ещё",
                    callback_data="watch_ad_confirm"
                )])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer("💰 +{} Coins!".format(AD_REWARD_COINS))
            
            logger.info(f"✅ User {user.telegram_id} watched ad and got {AD_REWARD_COINS} coins")
    
    except Exception as e:
        logger.error(f"❌ Error in watch_ad_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
