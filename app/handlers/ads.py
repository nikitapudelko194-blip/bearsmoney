"""In-game advertising system."""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

# Ad rewards
AD_REWARD_COINS = 100
AD_DAILY_LIMIT = 10


@router.callback_query(F.data == "watch_ad")
async def watch_ad_menu(query: CallbackQuery):
    """Show ad watching menu."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Count ads watched today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ads_query = select(CoinTransaction).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'ad_reward',
                CoinTransaction.created_at >= today_start
            )
            ads_result = await session.execute(ads_query)
            ads_watched = len(ads_result.scalars().all())
            
            remaining = AD_DAILY_LIMIT - ads_watched
            
            text = (
                f"📺 **Реклама**\n\n"
                f"Смотрите рекламу и получайте награды!\n\n"
                f"🎁 **Награда:** {AD_REWARD_COINS} Coins\n"
                f"📊 **Просмотрено сегодня:** {ads_watched}/{AD_DAILY_LIMIT}\n"
                f"⏳ **Осталось:** {remaining} просмотров\n\n"
            )
            
            if remaining > 0:
                text += "💡 Нажмите кнопку ниже, чтобы посмотреть рекламу!"
            else:
                text += "⏰ Лимит исчерпан! Приходите завтра."
            
            keyboard = []
            
            if remaining > 0:
                keyboard.append([InlineKeyboardButton(text="📺 Посмотреть рекламу", callback_data="do_watch_ad")])
            
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


@router.callback_query(F.data == "do_watch_ad")
async def do_watch_ad(query: CallbackQuery):
    """Simulate watching ad and give reward."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Count ads watched today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ads_query = select(CoinTransaction).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'ad_reward',
                CoinTransaction.created_at >= today_start
            )
            ads_result = await session.execute(ads_query)
            ads_watched = len(ads_result.scalars().all())
            
            if ads_watched >= AD_DAILY_LIMIT:
                await query.answer("⏰ Лимит просмотров исчерпан!", show_alert=True)
                return
            
            # Add reward
            user.coins += AD_REWARD_COINS
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=AD_REWARD_COINS,
                transaction_type='ad_reward',
                description='Просмотр рекламы'
            )
            session.add(transaction)
            
            await session.commit()
            
            remaining = AD_DAILY_LIMIT - ads_watched - 1
            
            text = (
                f"✅ **Награда получена!**\n\n"
                f"🎁 +{AD_REWARD_COINS} Coins\n"
                f"💼 Новый баланс: {user.coins:,.0f} Coins\n\n"
                f"📊 Просмотрено сегодня: {ads_watched + 1}/{AD_DAILY_LIMIT}\n"
                f"⏳ Осталось: {remaining} просмотров\n\n"
                f"💡 {'Смотрите еще!' if remaining > 0 else 'Приходите завтра!'}"
            )
            
            keyboard = []
            
            if remaining > 0:
                keyboard.append([InlineKeyboardButton(text="📺 Еще реклама", callback_data="do_watch_ad")])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer("🎉 +100 Coins!")
            logger.info(f"✅ User {user.telegram_id} watched ad, earned {AD_REWARD_COINS} coins")
    
    except Exception as e:
        logger.error(f"❌ Error in do_watch_ad: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
