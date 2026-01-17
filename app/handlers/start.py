"""Start command handler with referral support."""
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()

REFERRAL_BONUS = 500  # Bonus for both referrer and referred user


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handle /start command with referral support.
    Format: /start or /start ref_123456
    """
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        
        # Extract referral code if present
        referrer_id = None
        args = message.text.split()
        if len(args) > 1 and args[1].startswith('ref_'):
            try:
                referrer_id = int(args[1].replace('ref_', ''))
            except ValueError:
                logger.warning(f"⚠️ Invalid referral code: {args[1]}")
        
        async with get_session() as session:
            # Check if user exists
            query = select(User).where(User.telegram_id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            is_new_user = False
            
            if not user:
                # Create new user
                user = User(
                    telegram_id=user_id,
                    username=username,
                    first_name=first_name,
                    coins=1000,  # Starting bonus
                    ton_balance=0,
                    level=1,
                    experience=0
                )
                
                # Process referral if present
                if referrer_id and referrer_id != user_id:
                    # Find referrer
                    referrer_query = select(User).where(User.telegram_id == referrer_id)
                    referrer_result = await session.execute(referrer_query)
                    referrer = referrer_result.scalar_one_or_none()
                    
                    if referrer:
                        # Set referral relationship
                        user.referred_by = referrer_id
                        
                        # Give bonus to referrer
                        referrer.coins += REFERRAL_BONUS
                        referrer.referred_count += 1
                        referrer.referral_earnings_tier1 = (referrer.referral_earnings_tier1 or 0) + REFERRAL_BONUS
                        
                        # Give bonus to new user
                        user.coins += REFERRAL_BONUS
                        
                        # Log transactions
                        session.add(CoinTransaction(
                            user_id=referrer.id,
                            amount=REFERRAL_BONUS,
                            transaction_type='referral_bonus',
                            description=f'Бонус за приглашение @{username or user_id}'
                        ))
                        
                        session.add(CoinTransaction(
                            user_id=user.id,
                            amount=REFERRAL_BONUS,
                            transaction_type='referral_bonus',
                            description=f'Бонус за регистрацию по реферальной ссылке'
                        ))
                        
                        logger.info(f"✅ Referral: {referrer_id} invited {user_id}")
                
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                is_new_user = True
                logger.info(f"✅ New user registered: {user_id} (@{username})")
            
            # Welcome message
            if is_new_user:
                text = (
                    f"👋 **Добро пожаловать, {first_name}!**\n\n"
                    f"🐻 Добро пожаловать в **BearsMoney** - игру, где медведи зарабатывают деньги!\n\n"
                    f"🎁 **Стартовый бонус:** {user.coins:,.0f} Coins\n"
                )
                
                if user.referred_by:
                    text += f"\n🎉 +{REFERRAL_BONUS:,} Coins за регистрацию по реферальной ссылке!\n"
                
                text += (
                    f"\n🚀 **Начни играть:**\n"
                    f"• 🐻 Покупай медведей\n"
                    f"• 💰 Зарабатывай Coins\n"
                    f"• 💎 Обменивай на TON\n"
                    f"• 👥 Приглашай друзей\n"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📚 Пройти обучение", callback_data="tutorial")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
                ])
            else:
                # Returning user
                text = (
                    f"👋 **С возвращением, {first_name}!**\n\n"
                    f"💼 Баланс: {user.coins:,.0f} Coins\n"
                    f"💎 TON: {float(user.ton_balance):.4f}\n"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
                ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    except Exception as e:
        logger.error(f"❌ Error in cmd_start: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка. Попробуйте ещё раз."
        )


@router.callback_query(F.data == "main_menu")
async def main_menu(query: CallbackQuery):
    """
    Show main menu.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                f"🏠 **Главное меню**\n\n"
                f"👤 {query.from_user.first_name}\n"
                f"💼 Баланс: {user.coins:,.0f} Coins\n"
                f"💎 TON: {float(user.ton_balance):.4f}\n"
                f"⭐ Уровень: {user.level}\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🐻 Медведи", callback_data="bears"),
                    InlineKeyboardButton(text="🛒 Магазин", callback_data="shop"),
                ],
                [
                    InlineKeyboardButton(text="🎲 Кейсы", callback_data="cases"),
                    InlineKeyboardButton(text="💱 Обмен", callback_data="exchange"),
                ],
                [
                    InlineKeyboardButton(text="🎉 Ежедневно", callback_data="daily_rewards"),
                    InlineKeyboardButton(text="📺 Реклама", callback_data="watch_ad"),
                ],
                [
                    InlineKeyboardButton(text="⭐ Premium", callback_data="premium"),
                    InlineKeyboardButton(text="🖼️ NFT", callback_data="nft_marketplace"),
                ],
                [
                    InlineKeyboardButton(text="⚔️ PvP", callback_data="pvp_battles"),
                    InlineKeyboardButton(text="🔧 Улучшения", callback_data="bear_upgrades"),
                ],
                [
                    InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
                    InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
                ],
                [
                    InlineKeyboardButton(text="📚 Обучение", callback_data="tutorial"),
                    InlineKeyboardButton(text="🤝 Партнёры", callback_data="partnerships"),
                ],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in main_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
