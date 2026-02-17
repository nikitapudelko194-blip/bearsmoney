"""Daily rewards and fortune wheel handlers."""
import logging
import random
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, UserDailyLogin, CoinTransaction
from decimal import Decimal

logger = logging.getLogger(__name__)
router = Router()

# Daily rewards by day (starting at 50, +50 each day)
DAILY_REWARDS = {
    1: 50,
    2: 100,
    3: 150,
    4: 200,
    5: 250,
    6: 300,
    7: 350,   # Week bonus
    8: 400,
    9: 450,
    10: 500,
    11: 550,
    12: 600,
    13: 650,
    14: 700,  # 2 weeks bonus
    15: 750,
    16: 800,
    17: 850,
    18: 900,
    19: 950,
    20: 1000,
    21: 1050,  # 3 weeks bonus
    22: 1100,
    23: 1150,
    24: 1200,
    25: 1250,
    26: 1300,
    27: 1350,
    28: 1400,
    29: 1450,
    30: 1500,  # Month bonus!
}

# Fortune wheel prizes
FORTUNE_WHEEL_PRIZES = [
    {"type": "coins", "amount": 50, "emoji": "🪙", "weight": 30},
    {"type": "coins", "amount": 100, "emoji": "🪙", "weight": 25},
    {"type": "coins", "amount": 250, "emoji": "🪙🪙", "weight": 20},
    {"type": "coins", "amount": 500, "emoji": "💰", "weight": 15},
    {"type": "coins", "amount": 1000, "emoji": "💰💰", "weight": 7},
    {"type": "ton", "amount": 0.001, "emoji": "💎", "weight": 2},
    {"type": "ton", "amount": 0.005, "emoji": "💎💎", "weight": 0.8},
    {"type": "jackpot", "amount": 5000, "emoji": "🎆", "weight": 0.2},
]


async def get_or_create_daily_login(user_id: int, session: AsyncSession) -> UserDailyLogin:
    """
    Get or create daily login record.
    """
    query = select(UserDailyLogin).where(UserDailyLogin.user_id == user_id)
    result = await session.execute(query)
    daily_login = result.scalar_one_or_none()
    
    if not daily_login:
        daily_login = UserDailyLogin(
            user_id=user_id,
            streak_days=0,
            total_logins=0,
            last_login_date=None,
            reward_claimed_today=False
        )
        session.add(daily_login)
        await session.commit()
        await session.refresh(daily_login)
    
    return daily_login


async def check_and_update_streak(daily_login: UserDailyLogin, session: AsyncSession) -> bool:
    """
    Check if streak is valid and update it.
    Returns True if user can claim today's reward.
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # First login ever
    if not daily_login.last_login_date:
        daily_login.streak_days = 1
        daily_login.total_logins = 1
        daily_login.last_login_date = now
        daily_login.reward_claimed_today = False
        await session.commit()
        return True
    
    last_login = daily_login.last_login_date
    last_login_start = last_login.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Already claimed today
    if last_login_start == today_start and daily_login.reward_claimed_today:
        return False
    
    # Same day but not claimed yet
    if last_login_start == today_start:
        return True
    
    # Next day - increase streak
    if last_login_start == today_start - timedelta(days=1):
        daily_login.streak_days += 1
        if daily_login.streak_days > 30:
            daily_login.streak_days = 1  # Reset after 30 days
        daily_login.total_logins += 1
        daily_login.last_login_date = now
        daily_login.reward_claimed_today = False
        await session.commit()
        return True
    
    # Missed a day - reset streak
    daily_login.streak_days = 1
    daily_login.total_logins += 1
    daily_login.last_login_date = now
    daily_login.reward_claimed_today = False
    await session.commit()
    return True


@router.callback_query(F.data == "daily_rewards")
async def daily_rewards_menu(query: CallbackQuery):
    """
    Show daily rewards menu.
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get or create daily login
            daily_login = await get_or_create_daily_login(user.id, session)
            
            # Check streak
            can_claim = await check_and_update_streak(daily_login, session)
            
            # Refresh to get updated data
            await session.refresh(daily_login)
            
            # Get reward for current day
            current_day = daily_login.streak_days
            reward = DAILY_REWARDS.get(current_day, 50)
            
            # Calculate next milestone
            milestones = [7, 14, 21, 30]
            next_milestone = next((m for m in milestones if m > current_day), 30)
            days_to_milestone = next_milestone - current_day
            milestone_reward = DAILY_REWARDS.get(next_milestone, 1000)
            
            text = (
                f"🎉 **Ежедневные награды**\n\n"
                f"🔥 **Текущая серия:** {current_day} дней\n"
                f"🎯 **Всего входов:** {daily_login.total_logins}\n"
                f"🎁 **Награда сегодня:** {reward:,} Coins\n\n"
            )
            
            if not can_claim or daily_login.reward_claimed_today:
                text += (
                    f"✅ **Награда получена!**\n"
                    f"⏰ Приходи завтра за новой наградой!\n\n"
                )
            else:
                text += (
                    f"🎁 **Забери награду!**\n\n"
                )
            
            text += (
                f"🎯 **Следующая веха:**\n"
                f"🏆 День {next_milestone}: {milestone_reward:,} Coins\n"
                f"📅 Осталось: {days_to_milestone} дней\n\n"
                f"💡 **Совет:** Заходи каждый день, чтобы не потерять серию!\n"
            )
            
            keyboard = []
            
            # Add claim button if can claim
            if can_claim and not daily_login.reward_claimed_today:
                keyboard.append([InlineKeyboardButton(text="🎁 Забрать награду", callback_data="claim_daily_reward")])
            
            # Add fortune wheel button (available once per day)
            if not daily_login.reward_claimed_today:
                keyboard.append([InlineKeyboardButton(text="🎰 Крутить колесо фортуны", callback_data="fortune_wheel")])
            
            keyboard.append([InlineKeyboardButton(text="📅 Календарь наград", callback_data="rewards_calendar")])
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in daily_rewards_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "claim_daily_reward")
async def claim_daily_reward(query: CallbackQuery):
    """
    Claim daily reward.
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get daily login
            daily_login = await get_or_create_daily_login(user.id, session)
            await check_and_update_streak(daily_login, session)
            await session.refresh(daily_login)
            
            # Check if already claimed
            if daily_login.reward_claimed_today:
                await query.answer("✅ Вы уже получили награду сегодня!", show_alert=True)
                return
            
            # Get reward
            current_day = daily_login.streak_days
            reward = DAILY_REWARDS.get(current_day, 50)
            
            # Add coins
            user.coins += reward
            
            # Mark as claimed
            daily_login.reward_claimed_today = True
            daily_login.last_reward_claimed_at = datetime.utcnow()
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=reward,
                transaction_type='daily_reward',
                description=f'Ежедневная награда (день {current_day})'
            )
            session.add(transaction)
            
            await session.commit()
            
            # Success message
            text = (
                f"✅ **Награда получена!**\n\n"
                f"🎁 +{reward:,} Coins\n"
                f"🔥 Серия: {current_day} дней\n\n"
                f"💰 Новый баланс: {user.coins:,.0f} Coins\n\n"
                f"💡 Приходи завтра за новой наградой!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎰 Крутить колесо", callback_data="fortune_wheel")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 Поздравляем!")
            
            logger.info(f"✅ User {user.telegram_id} claimed daily reward: {reward} coins (day {current_day})")
    
    except Exception as e:
        logger.error(f"❌ Error in claim_daily_reward: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "fortune_wheel")
async def fortune_wheel(query: CallbackQuery):
    """
    Spin fortune wheel (once per day).
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get daily login
            daily_login = await get_or_create_daily_login(user.id, session)
            await session.refresh(daily_login)
            
            # Check if already spun today
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            last_spin_date = daily_login.last_reward_claimed_at
            
            if last_spin_date:
                last_spin_start = last_spin_date.replace(hour=0, minute=0, second=0, microsecond=0)
                if last_spin_start >= today_start:
                    await query.answer("⏰ Колесо уже кручено сегодня! Приходи завтра.", show_alert=True)
                    return
            
            # Weighted random selection
            weights = [p["weight"] for p in FORTUNE_WHEEL_PRIZES]
            prize = random.choices(FORTUNE_WHEEL_PRIZES, weights=weights, k=1)[0]
            
            # Add prize
            if prize["type"] == "coins":
                user.coins += prize["amount"]
                prize_text = f"{prize['amount']:,} Coins"
            elif prize["type"] == "ton":
                user.ton_balance += Decimal(str(prize["amount"]))
                prize_text = f"{prize['amount']:.4f} TON"
            elif prize["type"] == "jackpot":
                user.coins += prize["amount"]
                prize_text = f"🎆 JACKPOT: {prize['amount']:,} Coins!"
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=prize["amount"] if prize["type"] == "coins" else 0,
                transaction_type='fortune_wheel',
                description=f'Колесо фортуны: {prize_text}'
            )
            session.add(transaction)
            
            # Update last spin time
            daily_login.last_reward_claimed_at = now
            
            await session.commit()
            
            # Success message
            text = (
                f"🎰 **Колесо Фортуны**\n\n"
                f"🎯 Вы получили: {prize['emoji']}\n"
                f"🎁 **{prize_text}**\n\n"
                f"💰 Новый баланс:\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n\n"
                f"⏰ Следующее вращение: завтра"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎉 Ежедневные награды", callback_data="daily_rewards")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer(f"🎉 {prize['emoji']} {prize_text}!")
            
            logger.info(f"✅ User {user.telegram_id} won from fortune wheel: {prize_text}")
    
    except Exception as e:
        logger.error(f"❌ Error in fortune_wheel: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "rewards_calendar")
async def rewards_calendar(query: CallbackQuery):
    """
    Show 30-day rewards calendar.
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get daily login
            daily_login = await get_or_create_daily_login(user.id, session)
            await session.refresh(daily_login)
            
            current_day = daily_login.streak_days
            
            text = (
                f"📅 **Календарь наград**\n\n"
                f"🔥 Текущая серия: {current_day} дней\n\n"
            )
            
            # Show first week
            text += "📅 **Неделя 1:**\n"
            for day in range(1, 8):
                reward = DAILY_REWARDS[day]
                emoji = "✅" if day <= current_day else "🔒"
                bonus = " 🎉" if day == 7 else ""
                text += f"{emoji} День {day}: {reward:,} Coins{bonus}\n"
            
            # Show second week
            text += "\n📅 **Неделя 2:**\n"
            for day in range(8, 15):
                reward = DAILY_REWARDS[day]
                emoji = "✅" if day <= current_day else "🔒"
                bonus = " 🎉" if day == 14 else ""
                text += f"{emoji} День {day}: {reward:,} Coins{bonus}\n"
            
            # Show third week
            text += "\n📅 **Неделя 3:**\n"
            for day in range(15, 22):
                reward = DAILY_REWARDS[day]
                emoji = "✅" if day <= current_day else "🔒"
                bonus = " 🎉" if day == 21 else ""
                text += f"{emoji} День {day}: {reward:,} Coins{bonus}\n"
            
            # Show fourth week
            text += "\n📅 **Неделя 4:**\n"
            for day in range(22, 31):
                reward = DAILY_REWARDS[day]
                emoji = "✅" if day <= current_day else "🔒"
                bonus = " 🎆" if day == 30 else ""
                text += f"{emoji} День {day}: {reward:,} Coins{bonus}\n"
            
            text += "\n💡 Заходи каждый день, чтобы не потерять серию!"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К наградам", callback_data="daily_rewards")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in rewards_calendar: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
