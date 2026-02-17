"""Referral system handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.db import get_session
from app.database.models import User
from config import settings

logger = logging.getLogger(__name__)
router = Router()

# Referral rewards
REFERRAL_TIER1_PERCENT = 0.20  # 20% from tier 1
REFERRAL_TIER2_PERCENT = 0.10  # 10% from tier 2
REFERRAL_TIER3_PERCENT = 0.05  # 5% from tier 3


def generate_referral_link(telegram_id: int) -> str:
    """Generate referral link for user."""
    return f"https://t.me/{settings.BOT_USERNAME}?start=ref{telegram_id}"


@router.callback_query(F.data == "referrals")
async def referrals_menu(query: CallbackQuery):
    """Show referrals menu with link and statistics."""
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get referrals count
            tier1_query = select(User).where(User.referred_by == user.telegram_id)
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            tier1_count = len(tier1_users)
            
            # Count tier 2 referrals
            tier2_count = 0
            for t1 in tier1_users:
                t2_query = select(func.count(User.id)).where(User.referred_by == t1.telegram_id)
                t2_result = await session.execute(t2_query)
                tier2_count += t2_result.scalar() or 0
            
            # Generate referral link
            referral_link = generate_referral_link(user.telegram_id)
            
            # Calculate total earnings
            total_earnings = (
                (user.referral_earnings_tier1 or 0) +
                (user.referral_earnings_tier2 or 0) +
                (user.referral_earnings_tier3 or 0)
            )
            
            text = (
                f"👥 **Реферальная система**\n\n"
                f"💡 Приглашай друзей и получай % с их доходов!\n\n"
                f"🎁 **Ваша реферальная ссылка:**\n"
                f"`{referral_link}`\n\n"
                f"📊 **Ваша статистика:**\n"
                f"├ 👤 Приглашено: {tier1_count} чел\n"
                f"├ 🌳 Сеть 2-го уровня: {tier2_count} чел\n"
                f"└ 💰 Заработано: {total_earnings:,.0f} коинов\n\n"
                f"💎 **Уровни вознаграждений:**\n"
                f"🥇 1-й круг: {int(REFERRAL_TIER1_PERCENT*100)}% от доходов\n"
                f"🥈 2-й круг: {int(REFERRAL_TIER2_PERCENT*100)}% от доходов\n"
                f"🥉 3-й круг: {int(REFERRAL_TIER3_PERCENT*100)}% от доходов\n\n"
            )
            
            # Add premium bonus info
            if user.is_premium:
                text += "⭐ **Premium бонус:** +10% к реферальным наградам!\n\n"
            
            text += "💡 Скопируйте ссылку и отправьте друзьям!"
            
            keyboard = []
            
            # Add button to view referrals list if any
            if tier1_count > 0:
                keyboard.append([InlineKeyboardButton(text="📋 Мои рефералы", callback_data="referrals_list")])
            
            keyboard.append([InlineKeyboardButton(text="📊 Подробная статистика", callback_data="referrals_stats")])
            keyboard.append([InlineKeyboardButton(text="❓ Как это работает", callback_data="referrals_help")])
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in referrals_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "referrals_list")
async def referrals_list(query: CallbackQuery):
    """Show list of referrals."""
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get tier 1 referrals
            tier1_query = select(User).where(User.referred_by == user.telegram_id).order_by(User.created_at.desc())
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            
            if not tier1_users:
                text = (
                    f"👥 **Мои рефералы**\n\n"
                    f"У вас пока нет рефералов.\n\n"
                    f"💡 Пригласите друзей, чтобы получать % с их доходов!"
                )
            else:
                text = (
                    f"👥 **Мои рефералы** ({len(tier1_users)})\n\n"
                )
                
                for idx, ref in enumerate(tier1_users[:20], 1):
                    # Count their referrals
                    tier2_query = select(func.count(User.id)).where(User.referred_by == ref.telegram_id)
                    tier2_result = await session.execute(tier2_query)
                    tier2_count = tier2_result.scalar() or 0
                    
                    username = f"@{ref.username}" if ref.username else ref.first_name or "Пользователь"
                    network = f" (+{tier2_count})" if tier2_count > 0 else ""
                    
                    text += f"{idx}. {username}{network}\n"
                    text += f"   ├ 💰 Баланс: {ref.coins:,.0f} к\n"
                    text += f"   └ 📅 Присоединился: {ref.created_at.strftime('%d.%m.%Y')}\n"
                
                if len(tier1_users) > 20:
                    text += f"\n... и еще {len(tier1_users) - 20} рефералов\n"
                
                text += "\n💡 Чем активнее ваши рефералы, тем больше вы зарабатываете!"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="referrals")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in referrals_list: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "referrals_stats")
async def referrals_stats(query: CallbackQuery):
    """Show detailed referral statistics."""
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get tier 1
            tier1_query = select(User).where(User.referred_by == user.telegram_id)
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            
            # Count tier 2
            tier2_count = 0
            for t1 in tier1_users:
                t2_query = select(func.count(User.id)).where(User.referred_by == t1.telegram_id)
                t2_result = await session.execute(t2_query)
                tier2_count += t2_result.scalar() or 0
            
            # Calculate earnings
            tier1_earnings = user.referral_earnings_tier1 or 0
            tier2_earnings = user.referral_earnings_tier2 or 0
            tier3_earnings = user.referral_earnings_tier3 or 0
            total_earnings = tier1_earnings + tier2_earnings + tier3_earnings
            
            # Calculate potential daily income from referrals
            tier1_potential = 0
            for ref in tier1_users:
                # Get their bears income
                bears_query = select(func.sum(Bear.coins_per_day)).where(Bear.owner_id == ref.id)
                bears_result = await session.execute(bears_query)
                daily_income = bears_result.scalar() or 0
                tier1_potential += daily_income * REFERRAL_TIER1_PERCENT
            
            text = (
                f"📊 **Детальная статистика**\n\n"
                f"🌳 **Реферальная сеть:**\n"
                f"├ 🥇 1-й круг: {len(tier1_users)} чел ({int(REFERRAL_TIER1_PERCENT*100)}%)\n"
                f"├ 🥈 2-й круг: {tier2_count} чел ({int(REFERRAL_TIER2_PERCENT*100)}%)\n"
                f"└ 🥉 3-й круг: 0 чел ({int(REFERRAL_TIER3_PERCENT*100)}%)\n\n"
                f"💰 **Заработано:**\n"
                f"├ Tier 1: {tier1_earnings:,.0f} к\n"
                f"├ Tier 2: {tier2_earnings:,.0f} к\n"
                f"├ Tier 3: {tier3_earnings:,.0f} к\n"
                f"└ 💸 Всего: {total_earnings:,.0f} коинов\n\n"
                f"📈 **Потенциальный доход:**\n"
                f"💵 От 1-го круга: ~{tier1_potential:.0f} к/день\n"
                f"📆 Прогноз/месяц: ~{tier1_potential * 30:,.0f} к\n\n"
            )
            
            if len(tier1_users) > 0:
                # Find most profitable referral
                best_ref = max(tier1_users, key=lambda x: x.coins, default=None)
                if best_ref:
                    username = f"@{best_ref.username}" if best_ref.username else best_ref.first_name
                    text += f"🏆 **Лучший реферал:** {username} ({best_ref.coins:,.0f} к)\n\n"
            
            text += (
                f"💡 **Совет:**\n"
                f"Приглашайте активных игроков - ваш доход растет вместе с их успехом!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="referrals")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in referrals_stats: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "referrals_help")
async def referrals_help(query: CallbackQuery):
    """Show referral system explanation."""
    text = (
        f"❓ **Как работает реферальная система**\n\n"
        f"🎯 **Принцип:**\n"
        f"Вы получаете процент от заработка ваших рефералов!\n\n"
        f"🌳 **3 уровня сети:**\n"
        f"🥇 **1-й круг** (20%): Люди, которых пригласили ВЫ\n"
        f"🥈 **2-й круг** (10%): Люди, которых пригласили ваши рефералы\n"
        f"🥉 **3-й круг** (5%): Следующий уровень глубины\n\n"
        f"💰 **Что считается доходом:**\n"
        f"• Заработок от медведей\n"
        f"• Награды за задания\n"
        f"• Бонусы и призы\n\n"
        f"⭐ **Premium бонус:**\n"
        f"С подпиской Premium вы получаете +10% к реферальным наградам!\n\n"
        f"📊 **Пример:**\n"
        f"Ваш реферал заработал 1000 коинов\n"
        f"└ Вы получаете: 200 коинов (20%)\n\n"
        f"🚀 **Как увеличить доход:**\n"
        f"1. Приглашайте больше людей\n"
        f"2. Помогайте им развиваться\n"
        f"3. Купите Premium для +10%\n\n"
        f"💡 Реферальные награды начисляются автоматически!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="referrals")],
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    await query.answer()
