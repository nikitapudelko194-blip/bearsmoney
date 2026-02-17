"""Referral system handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.db import get_session
from app.database.models import User, Bear
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
            
            # Get referrals count (referred_by contains user.id, not telegram_id)
            tier1_query = select(User).where(User.referred_by == user.id)
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            tier1_count = len(tier1_users)
            
            # Count tier 2 referrals
            tier2_count = 0
            for t1 in tier1_users:
                t2_query = select(func.count(User.id)).where(User.referred_by == t1.id)
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
                f"👥 <b>Реферальная система</b>\n\n"
                f"💡 Приглашай друзей и получай <b>100 Coins</b> за каждого!\n\n"
                f"🎁 <b>Ваша реферальная ссылка:</b>\n"
                f"<code>{referral_link}</code>\n\n"
                f"📊 <b>Ваша статистика:</b>\n"
                f"├ 👤 Приглашено: <b>{tier1_count}</b> чел\n"
                f"├ 🌳 Сеть 2-го уровня: <b>{tier2_count}</b> чел\n"
                f"└ 💰 Заработано: <b>{total_earnings:,.0f}</b> коинов\n\n"
                f"💎 <b>Уровни вознаграждений:</b>\n"
                f"🥇 1-й круг: {int(REFERRAL_TIER1_PERCENT*100)}% от доходов\n"
                f"🥈 2-й круг: {int(REFERRAL_TIER2_PERCENT*100)}% от доходов\n"
                f"🥉 3-й круг: {int(REFERRAL_TIER3_PERCENT*100)}% от доходов\n\n"
            )
            
            # Add premium bonus info
            if user.is_premium:
                text += "⭐ <b>Premium бонус:</b> +10% к реферальным наградам!\n\n"
            
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
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
            
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
            tier1_query = select(User).where(User.referred_by == user.id).order_by(User.created_at.desc())
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            
            if not tier1_users:
                text = (
                    f"👥 <b>Мои рефералы</b>\n\n"
                    f"У вас пока нет рефералов.\n\n"
                    f"💡 Пригласите друзей, чтобы получать % с их доходов!"
                )
            else:
                text = (
                    f"👥 <b>Мои рефералы</b> ({len(tier1_users)})\n\n"
                )
                
                for idx, ref in enumerate(tier1_users[:20], 1):
                    # Count their referrals
                    tier2_query = select(func.count(User.id)).where(User.referred_by == ref.id)
                    tier2_result = await session.execute(tier2_query)
                    tier2_count = tier2_result.scalar() or 0
                    
                    username = f"@{ref.username}" if ref.username else ref.first_name or "Пользователь"
                    network = f" (+{tier2_count})" if tier2_count > 0 else ""
                    
                    text += f"{idx}. <b>{username}</b>{network}\n"
                    text += f"   ├ 💰 Баланс: {ref.coins:,.0f} к\n"
                    text += f"   └ 📅 Присоединился: {ref.created_at.strftime('%d.%m.%Y')}\n"
                
                if len(tier1_users) > 20:
                    text += f"\n... и еще {len(tier1_users) - 20} рефералов\n"
                
                text += "\n💡 Чем активнее ваши рефералы, тем больше вы зарабатываете!"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="referrals")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
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
            tier1_query = select(User).where(User.referred_by == user.id)
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            
            # Count tier 2
            tier2_count = 0
            for t1 in tier1_users:
                t2_query = select(func.count(User.id)).where(User.referred_by == t1.id)
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
                f"📊 <b>Детальная статистика</b>\n\n"
                f"🌳 <b>Реферальная сеть:</b>\n"
                f"├ 🥇 1-й круг: {len(tier1_users)} чел ({int(REFERRAL_TIER1_PERCENT*100)}%)\n"
                f"├ 🥈 2-й круг: {tier2_count} чел ({int(REFERRAL_TIER2_PERCENT*100)}%)\n"
                f"└ 🥉 3-й круг: 0 чел ({int(REFERRAL_TIER3_PERCENT*100)}%)\n\n"
                f"💰 <b>Заработано:</b>\n"
                f"├ Tier 1: {tier1_earnings:,.0f} к\n"
                f"├ Tier 2: {tier2_earnings:,.0f} к\n"
                f"├ Tier 3: {tier3_earnings:,.0f} к\n"
                f"└ 💸 Всего: {total_earnings:,.0f} коинов\n\n"
                f"📈 <b>Потенциальный доход:</b>\n"
                f"💵 От 1-го круга: ~{tier1_potential:.0f} к/день\n"
                f"📆 Прогноз/месяц: ~{tier1_potential * 30:,.0f} к\n\n"
            )
            
            if len(tier1_users) > 0:
                # Find most profitable referral
                best_ref = max(tier1_users, key=lambda x: x.coins, default=None)
                if best_ref:
                    username = f"@{best_ref.username}" if best_ref.username else best_ref.first_name
                    text += f"🏆 <b>Лучший реферал:</b> {username} ({best_ref.coins:,.0f} к)\n\n"
            
            text += (
                f"💡 <b>Совет:</b>\n"
                f"Приглашайте активных игроков - ваш доход растет вместе с их успехом!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="referrals")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in referrals_stats: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "referrals_help")
async def referrals_help(query: CallbackQuery):
    """Show referral system explanation."""
    text = (
        f"❓ <b>Как работает реферальная система</b>\n\n"
        f"🎯 <b>Принцип:</b>\n"
        f"Вы получаете процент от заработка ваших рефералов!\n\n"
        f"🌳 <b>3 уровня сети:</b>\n"
        f"🥇 <b>1-й круг</b> (20%): Люди, которых пригласили ВЫ\n"
        f"🥈 <b>2-й круг</b> (10%): Люди, которых пригласили ваши рефералы\n"
        f"🥉 <b>3-й круг</b> (5%): Следующий уровень глубины\n\n"
        f"💰 <b>Что считается доходом:</b>\n"
        f"• Заработок от медведей\n"
        f"• Награды за задания\n"
        f"• Бонусы и призы\n\n"
        f"⭐ <b>Premium бонус:</b>\n"
        f"С подпиской Premium вы получаете +10% к реферальным наградам!\n\n"
        f"📊 <b>Пример:</b>\n"
        f"Ваш реферал заработал 1000 коинов\n"
        f"└ Вы получаете: 200 коинов (20%)\n\n"
        f"🚀 <b>Как увеличить доход:</b>\n"
        f"1. Приглашайте больше людей\n"
        f"2. Помогайте им развиваться\n"
        f"3. Купите Premium для +10%\n\n"
        f"💡 Реферальные награды начисляются автоматически!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="referrals")],
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await query.answer()
