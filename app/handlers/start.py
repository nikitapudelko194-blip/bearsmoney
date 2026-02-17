"""Start command handler with referral support."""
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction
from datetime import datetime
from app.bot import bot

logger = logging.getLogger(__name__)
router = Router()

REFERRAL_BONUS = 100  # Bonus for both referrer and referred user


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handle /start command with referral support.
    Format: /start or /start ref123456
    """
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        
        # Extract referral code if present
        referrer_telegram_id = None
        args = message.text.split()
        if len(args) > 1 and args[1].startswith('ref'):
            try:
                referrer_telegram_id = int(args[1].replace('ref', ''))
            except ValueError:
                logger.warning(f"⚠️ Invalid referral code: {args[1]}")
        
        async with get_session() as session:
            # Check if user exists
            query = select(User).where(User.telegram_id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            is_new_user = False
            referrer_notified = False
            
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
                if referrer_telegram_id and referrer_telegram_id != user_id:
                    # Find referrer by telegram_id
                    referrer_query = select(User).where(User.telegram_id == referrer_telegram_id)
                    referrer_result = await session.execute(referrer_query)
                    referrer = referrer_result.scalar_one_or_none()
                    
                    if referrer:
                        # Set referral relationship (save referrer's DB id, not telegram_id)
                        user.referred_by = referrer.id
                        
                        # Give bonus to referrer
                        referrer.coins += REFERRAL_BONUS
                        referrer.referred_count += 1
                        referrer.referral_earnings_tier1 = (referrer.referral_earnings_tier1 or 0) + REFERRAL_BONUS
                        
                        # Give bonus to new user
                        user.coins += REFERRAL_BONUS
                        
                        # Save user first to get ID
                        session.add(user)
                        await session.flush()  # Get user.id before creating transactions
                        
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
                        
                        await session.commit()
                        await session.refresh(user)
                        await session.refresh(referrer)
                        
                        logger.info(f"✅ Referral: {referrer_telegram_id} invited {user_id}")
                        
                        # Send notification to referrer
                        try:
                            referrer_username = f"@{username}" if username else first_name or f"ID: {user_id}"
                            notification_text = (
                                f"🎉 <b>Новый реферал!</b>\n\n"
                                f"👤 Пользователь <b>{referrer_username}</b> перешёл по вашей ссылке!\n"
                                f"💰 Вы получили: <b>+{REFERRAL_BONUS} Coins</b>\n\n"
                                f"💼 Ваш баланс: <b>{referrer.coins:,.0f} Coins</b>\n"
                                f"👥 Всего рефералов: <b>{referrer.referred_count}</b>"
                            )
                            
                            await bot.send_message(
                                chat_id=referrer.telegram_id,
                                text=notification_text,
                                parse_mode="HTML"
                            )
                            referrer_notified = True
                        except Exception as e:
                            logger.warning(f"⚠️ Could not send notification to referrer {referrer_telegram_id}: {e}")
                    else:
                        logger.warning(f"⚠️ Referrer {referrer_telegram_id} not found")
                        session.add(user)
                        await session.commit()
                        await session.refresh(user)
                else:
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                
                is_new_user = True
                logger.info(f"✅ New user registered: {user_id} (@{username})")
            
            # Welcome message
            if is_new_user:
                text = (
                    f"👋 <b>Добро пожаловать, {first_name}!</b>\n\n"
                    f"🐻 Добро пожаловать в <b>BearsMoney</b> - увлекательную игру про коллекционирование медведей!\n\n"
                    f"🎁 <b>Стартовый бонус:</b> {user.coins:,.0f} Coins\n"
                )
                
                if user.referred_by:
                    text += f"\n🎉 +{REFERRAL_BONUS:,} Coins за регистрацию по приглашению друга!\n"
                
                text += (
                    f"\n🎮 <b>Что делать в игре:</b>\n"
                    f"• 🐻 Собирай коллекцию уникальных медведей\n"
                    f"• ⬆️ Прокачивай их и делай сильнее\n"
                    f"• ⚔️ Сражайся с другими игроками\n"
                    f"• 🎁 Получай ежедневные награды\n"
                    f"• 👥 Играй с друзьями!\n"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📚 Пройти обучение", callback_data="tutorial")],
                    [InlineKeyboardButton(text="🏠 Начать игру!", callback_data="main_menu")],
                ])
            else:
                # Returning user
                text = (
                    f"👋 <b>С возвращением, {first_name}!</b>\n\n"
                    f"💼 Баланс: {user.coins:,.0f} Coins\n"
                    f"💎 TON: {float(user.ton_balance):.4f}\n"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
                ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
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
                f"🏠 <b>Главное меню</b>\n\n"
                f"👤 {query.from_user.first_name}\n"
                f"💼 Баланс: {user.coins:,.0f} Coins\n"
                f"💎 TON: {float(user.ton_balance):.4f}\n"
                f"⭐ Уровень: {user.level}\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears"),
                    InlineKeyboardButton(text="🛍️ Магазин", callback_data="shop"),
                ],
                [
                    InlineKeyboardButton(text="🎲 Кейсы", callback_data="cases"),
                    InlineKeyboardButton(text="💎 Пополнить", callback_data="exchange"),
                ],
                [
                    InlineKeyboardButton(text="🎁 Ежедневная награда", callback_data="daily_rewards"),
                    InlineKeyboardButton(text="📺 Бонусы", callback_data="watch_ad"),
                ],
                [
                    InlineKeyboardButton(text="⭐ Premium", callback_data="premium"),
                    InlineKeyboardButton(text="🖼️ NFT", callback_data="nft_marketplace"),
                ],
                [
                    InlineKeyboardButton(text="⚔️ PvP Битвы", callback_data="pvp_battles"),
                    InlineKeyboardButton(text="🚀 Улучшения", callback_data="upgrades"),
                ],
                [
                    InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="referrals"),
                    InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
                ],
                [
                    InlineKeyboardButton(text="📚 Обучение", callback_data="tutorial"),
                ],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in main_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "start")
async def start_callback(query: CallbackQuery):
    """
    Handle 'start' callback to return to main menu.
    """
    await main_menu(query)
