"""Referral system handler."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.db import get_session
from app.database.models import User
from config import settings

logger = logging.getLogger(__name__)
router = Router()

# Коэффициенты реферальной системы
REFERRAL_REWARDS = {
    1: 0.20,  # 20% от трат прямых рефералов
    2: 0.10,  # 10% от трат рефералов 2 уровня
    3: 0.05,  # 5% от трат рефералов 3 уровня
}


class ReferralService:
    """Service for referral system."""
    
    @staticmethod
    async def process_referral_earnings(session: AsyncSession, user_id: int, amount_spent: float):
        """
        Начислить реферальные выплаты за траты пользователя.
        Вызывается каждый раз, когда пользователь тратит коины.
        """
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user or not user.referred_by:
            return  # Нет реферера
        
        # Уровень 1: Прямой реферер (тот кто пригласил)
        level1_query = select(User).where(User.telegram_id == user.referred_by)
        level1_result = await session.execute(level1_query)
        level1_referrer = level1_result.scalar_one_or_none()
        
        if level1_referrer:
            level1_reward = amount_spent * REFERRAL_REWARDS[1]
            level1_referrer.coins += level1_reward
            level1_referrer.referral_earnings_tier1 = (level1_referrer.referral_earnings_tier1 or 0) + level1_reward
            logger.info(f"💰 Level 1 referral: User {level1_referrer.telegram_id} earned {level1_reward:.2f} from {user.telegram_id}")
            
            # Уровень 2: Реферер реферера
            if level1_referrer.referred_by:
                level2_query = select(User).where(User.telegram_id == level1_referrer.referred_by)
                level2_result = await session.execute(level2_query)
                level2_referrer = level2_result.scalar_one_or_none()
                
                if level2_referrer:
                    level2_reward = amount_spent * REFERRAL_REWARDS[2]
                    level2_referrer.coins += level2_reward
                    level2_referrer.referral_earnings_tier2 = (level2_referrer.referral_earnings_tier2 or 0) + level2_reward
                    logger.info(f"💰 Level 2 referral: User {level2_referrer.telegram_id} earned {level2_reward:.2f} from {user.telegram_id}")
                    
                    # Уровень 3: Реферер реферера реферера
                    if level2_referrer.referred_by:
                        level3_query = select(User).where(User.telegram_id == level2_referrer.referred_by)
                        level3_result = await session.execute(level3_query)
                        level3_referrer = level3_result.scalar_one_or_none()
                        
                        if level3_referrer:
                            level3_reward = amount_spent * REFERRAL_REWARDS[3]
                            level3_referrer.coins += level3_reward
                            level3_referrer.referral_earnings_tier3 = (level3_referrer.referral_earnings_tier3 or 0) + level3_reward
                            logger.info(f"💰 Level 3 referral: User {level3_referrer.telegram_id} earned {level3_reward:.2f} from {user.telegram_id}")
        
        await session.commit()


@router.callback_query(F.data == "referrals")
async def referrals_menu(query: CallbackQuery):
    """
    Show referral system menu.
    """
    try:
        async with get_session() as session:
            # Получаем пользователя
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Считаем рефералов по уровням (referred_by хранит telegram_id)
            # Уровень 1: прямые рефералы
            level1_query = select(func.count(User.id)).where(User.referred_by == user.telegram_id)
            level1_result = await session.execute(level1_query)
            level1_count = level1_result.scalar() or 0
            
            # Уровень 2: рефералы рефералов
            level1_users_query = select(User.telegram_id).where(User.referred_by == user.telegram_id)
            level1_users_result = await session.execute(level1_users_query)
            level1_telegram_ids = [row[0] for row in level1_users_result.fetchall()]
            
            level2_count = 0
            if level1_telegram_ids:
                level2_query = select(func.count(User.id)).where(User.referred_by.in_(level1_telegram_ids))
                level2_result = await session.execute(level2_query)
                level2_count = level2_result.scalar() or 0
            
            # Уровень 3: рефералы 3 уровня
            level2_users_query = select(User.telegram_id).where(User.referred_by.in_(level1_telegram_ids)) if level1_telegram_ids else None
            level3_count = 0
            if level2_users_query:
                level2_users_result = await session.execute(level2_users_query)
                level2_telegram_ids = [row[0] for row in level2_users_result.fetchall()]
                
                if level2_telegram_ids:
                    level3_query = select(func.count(User.id)).where(User.referred_by.in_(level2_telegram_ids))
                    level3_result = await session.execute(level3_query)
                    level3_count = level3_result.scalar() or 0
            
            # Заработок по уровням
            earnings_l1 = user.referral_earnings_tier1 or 0
            earnings_l2 = user.referral_earnings_tier2 or 0
            earnings_l3 = user.referral_earnings_tier3 or 0
            total_earnings = earnings_l1 + earnings_l2 + earnings_l3
            
            # Генерируем реферальную ссылку
            bot_username = (await query.bot.me()).username
            referral_link = f"https://t.me/{bot_username}?start=ref_{user.telegram_id}"
            
            text = (
                f"👥 **Реферальная программа**\n\n"
                f"🔗 **Ваша ссылка:**\n"
                f"`{referral_link}`\n\n"
                f"💡 *Нажмите на ссылку чтобы скопировать*\n\n"
                f"📊 **Ваша сеть:**\n\n"
                f"🥇 **1-й круг** (прямые рефералы)\n"
                f"├─ 👥 Приглашено: {level1_count} чел.\n"
                f"├─ 💰 Бонус: 20% от трат\n"
                f"└─ 💸 Получено: {earnings_l1:,.0f} коинов\n\n"
                f"🥈 **2-й круг** (рефералы рефералов)\n"
                f"├─ 👥 Приглашено: {level2_count} чел.\n"
                f"├─ 💰 Бонус: 10% от трат\n"
                f"└─ 💸 Получено: {earnings_l2:,.0f} коинов\n\n"
                f"🥉 **3-й круг**\n"
                f"├─ 👥 Приглашено: {level3_count} чел.\n"
                f"├─ 💰 Бонус: 5% от трат\n"
                f"└─ 💸 Получено: {earnings_l3:,.0f} коинов\n\n"
                f"💎 **Всего получено:** {total_earnings:,.0f} коинов\n\n"
                f"🎁 **Как работает:**\n"
                f"1️⃣ Друг регистрируется → оба получаете бонус\n"
                f"2️⃣ Друг тратит коины → вы получаете 20%\n"
                f"3️⃣ Его реферал тратит → вы получаете 10%\n"
                f"4️⃣ Строите сеть и получаете пассивный доход!\n\n"
                f"✨ Приглашайте друзей и получайте бонусы!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Список рефералов (1-й круг)", callback_data="referrals_list")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in referrals_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "referrals_list")
async def referrals_list(query: CallbackQuery):
    """
    Show list of referrals.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Получаем прямых рефералов (referred_by хранит telegram_id)
            refs_query = select(User).where(User.referred_by == user.telegram_id).order_by(User.created_at.desc()).limit(20)
            refs_result = await session.execute(refs_query)
            referrals = refs_result.scalars().all()
            
            if not referrals:
                text = (
                    "👥 **Ваши рефералы** (1-й круг)\n\n"
                    "У вас пока нет рефералов.\n\n"
                    "💡 Поделитесь своей ссылкой с друзьями!\n\n"
                    "🎁 За каждого приглашенного друга вы получите:\n"
                    "• Бонус при регистрации\n"
                    "• 20% от всех его трат в игре\n"
                    "• 10% от трат его рефералов\n"
                    "• 5% от трат рефералов 3-го уровня"
                )
            else:
                text = f"👥 **Ваши рефералы** (1-й круг)\n\n"
                text += f"📊 Всего приглашено: {len(referrals)}\n\n"
                
                for idx, ref in enumerate(referrals, 1):
                    name = ref.first_name or ref.username or "User"
                    username_str = f"@{ref.username}" if ref.username else "без username"
                    date_str = ref.created_at.strftime('%d.%m.%Y')
                    text += f"{idx}. {name} ({username_str})\n   📅 Присоединился: {date_str}\n\n"
                
                if len(referrals) == 20:
                    text += "\n... показаны последние 20 рефералов"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К реферальной программе", callback_data="referrals")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in referrals_list: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
