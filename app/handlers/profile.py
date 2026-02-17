"""Handlers for user profile."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.db import get_session
from app.database.models import User, Bear, CoinTransaction, P2PListing
from app.services.bears import BEAR_CLASSES, MAX_BEAR_LEVEL
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = Router()


def format_premium_status(user: User) -> str:
    """
    Format premium status with expiration.
    """
    if user.is_premium:
        if user.premium_until:
            time_left = user.premium_until - datetime.utcnow()
            if time_left.total_seconds() > 0:
                days = time_left.days
                hours = (time_left.total_seconds() % 86400) // 3600
                if days > 0:
                    return f"\n👳 **Премиум активен** ({days}д {hours}ч)"
                else:
                    return f"\n👳 **Премиум активен** ({hours}ч)"
        return "\n👳 **Премиум активен** (бессрочно)"
    return "\n⭕ Обычный пользователь"


@router.callback_query(F.data == "profile")
async def show_profile(query: CallbackQuery):
    """
    Show user profile with statistics.
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get bears stats
            bears_query = select(Bear).where(Bear.owner_id == user.id)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            # Calculate stats
            total_bears = len(bears)
            total_income_per_hour = sum(bear.coins_per_hour for bear in bears)
            total_income_per_day = sum(bear.coins_per_day for bear in bears)
            
            # Count bears by type
            bears_by_type = {}
            for bear in bears:
                bears_by_type[bear.bear_type] = bears_by_type.get(bear.bear_type, 0) + 1
            
            # Calculate average level
            avg_level = sum(bear.level for bear in bears) / total_bears if bears else 0
            max_level = max((bear.level for bear in bears), default=0)
            
            # Get total earned
            transaction_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'earn'
            )
            transaction_result = await session.execute(transaction_query)
            total_earned = transaction_result.scalar() or 0
            
            # Get referrals count
            referrals_query = select(func.count(User.id)).where(User.referred_by == user.telegram_id)
            referrals_result = await session.execute(referrals_query)
            referrals_count = referrals_result.scalar() or 0
            
            # Format text
            text = (
                f"👤 **Профиль {query.from_user.first_name}**\n\n"
                f"📊 **Основная информация**\n"
                f"🆔 ID: `{user.telegram_id}`\n"
                f"👤 @{query.from_user.username or 'не указано'}\n"
                f"⭐ Уровень: {user.level}\n"
                f"{format_premium_status(user)}\n\n"
                f"💰 **Финансы**\n"
                f"├ 🪙 Баланс: {user.coins:,.0f} коинов\n"
                f"├ 💎 TON: {user.ton_balance:.4f}\n"
                f"└ 💸 Всего заработано: {total_earned:,.0f} коинов\n\n"
                f"🐻 **Медведи** ({total_bears})\n"
            )
            
            # Add bears by type
            type_order = ['common', 'rare', 'epic', 'legendary']
            for bear_type in type_order:
                if bear_type in bears_by_type:
                    class_info = BEAR_CLASSES[bear_type]
                    count = bears_by_type[bear_type]
                    text += f"{class_info['color']} {class_info['rarity']}: {count}\n"
            
            text += (
                f"\n📈 **Статистика медведей**\n"
                f"💰 Доход/час: {total_income_per_hour:.1f} коинов\n"
                f"📅 Доход/день: {total_income_per_day:.1f} коинов\n"
                f"📊 Средний уровень: {avg_level:.1f}\n"
                f"🎯 Максимальный уровень: {max_level}/{MAX_BEAR_LEVEL}\n\n"
            )
            
            # Add referral info
            if referrals_count > 0:
                referral_earnings = (
                    (user.referral_earnings_tier1 or 0) +
                    (user.referral_earnings_tier2 or 0) +
                    (user.referral_earnings_tier3 or 0)
                )
                text += (
                    f"👥 **Рефералы**\n"
                    f"├ 👤 Приглашено: {referrals_count} чел\n"
                    f"└ 💰 Заработано: {referral_earnings:,.0f} к\n\n"
                )
            
            text += (
                f"📅 **Аккаунт**\n"
                f"📋 Создан: {user.created_at.strftime('%d.%m.%Y')}\n"
                f"🔄 Обновлен: {user.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            keyboard = [
                [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
                [InlineKeyboardButton(text="💰 Финансы", callback_data="finance_stats")],
                [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ]
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in show_profile: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ STATISTICS ============

@router.callback_query(F.data == "stats")
async def stats_menu(query: CallbackQuery):
    """
    Main statistics menu.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get basic stats
            bears_query = select(Bear).where(Bear.owner_id == user.id)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            days_in_game = (datetime.utcnow() - user.created_at).days
            total_bears = len(bears)
            
            # Get referrals count
            tier1_query = select(func.count(User.id)).where(User.referred_by == user.telegram_id)
            tier1_result = await session.execute(tier1_query)
            tier1_count = tier1_result.scalar() or 0
            
            total_ref_earnings = (
                (user.referral_earnings_tier1 or 0) +
                (user.referral_earnings_tier2 or 0) +
                (user.referral_earnings_tier3 or 0)
            )
            
            text = (
                f"📊 **Статистика**\n\n"
                f"🎮 **Игровая активность**\n"
                f"├ 🕐 В игре: {days_in_game} дней\n"
                f"├ ⭐ Уровень: {user.level}\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {user.ton_balance:.4f}\n\n"
                f"🐻 **Коллекция**\n"
                f"├ 📦 Медведей: {total_bears}\n"
                f"└ 💰 Доход: {sum(b.coins_per_day for b in bears):,.0f} к/день\n\n"
                f"👥 **Рефералы**\n"
                f"├ 👤 Приглашено: {tier1_count} чел\n"
                f"└ 💸 Заработано: {total_ref_earnings:,.0f} коинов\n\n"
                f"👉 Выберите категорию:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Общая", callback_data="stats_general"),
                    InlineKeyboardButton(text="💰 Финансы", callback_data="stats_finance"),
                ],
                [
                    InlineKeyboardButton(text="🐻 Медведи", callback_data="stats_bears"),
                    InlineKeyboardButton(text="🎁 Кейсы", callback_data="stats_cases"),
                ],
                [
                    InlineKeyboardButton(text="👥 Рефералы", callback_data="stats_referrals"),
                    InlineKeyboardButton(text="🏆 Достижения", callback_data="stats_achievements"),
                ],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in stats_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "stats_general")
async def stats_general(query: CallbackQuery):
    """
    General statistics.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            bears_query = select(Bear).where(Bear.owner_id == user.id)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            days_in_game = (datetime.utcnow() - user.created_at).days + 1
            
            # Count by type
            bears_by_type = {}
            for bear in bears:
                bears_by_type[bear.bear_type] = bears_by_type.get(bear.bear_type, 0) + 1
            
            text = (
                f"📊 **Общая статистика**\n\n"
                f"🎮 **Игровая активность**\n"
                f"├ 🕐 В игре: {days_in_game} дней\n"
                f"├ 📅 Создан: {user.created_at.strftime('%d.%m.%Y')}\n"
                f"└ ⏰ Последний визит: сегодня\n\n"
                f"🐻 **Коллекция медведей**\n"
                f"├ 📦 Всего: {len(bears)}\n"
            )
            
            for bear_type in ['common', 'rare', 'epic', 'legendary']:
                if bear_type in bears_by_type:
                    class_info = BEAR_CLASSES[bear_type]
                    text += f"├ {class_info['color']} {class_info['rarity']}: {bears_by_type[bear_type]}\n"
            
            avg_level = sum(b.level for b in bears) / len(bears) if bears else 0
            text += f"└ 📊 Ср. уровень: {avg_level:.1f}\n\n"
            
            text += (
                f"💰 **Экономика**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"├ 💎 TON: {user.ton_balance:.4f}\n"
                f"└ ⭐ Уровень: {user.level}\n\n"
                f"🚀 **Прогресс**\n"
                f"├ 🎯 Опыт: {user.experience:.0f}\n"
                f"└ 📈 Активность: высокая"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К статистике", callback_data="stats")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in stats_general: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "stats_finance")
async def stats_finance(query: CallbackQuery):
    """
    Finance statistics.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get income
            earned_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type.in_(['earn', 'referral_tier1', 'referral_tier2', 'referral_tier3'])
            )
            earned_result = await session.execute(earned_query)
            total_earned = earned_result.scalar() or 0
            
            # Get expenses
            spent_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'spend'
            )
            spent_result = await session.execute(spent_query)
            total_spent = abs(spent_result.scalar() or 0)
            
            # Weekly stats
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.created_at >= week_ago
            )
            week_result = await session.execute(week_query)
            week_earnings = week_result.scalar() or 0
            
            # Bears income
            bears_query = select(Bear).where(Bear.owner_id == user.id)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            daily_income = sum(b.coins_per_day for b in bears)
            
            profit = total_earned - total_spent
            
            text = (
                f"💰 **Финансовая статистика**\n\n"
                f"💼 **Текущий баланс**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {user.ton_balance:.4f}\n\n"
                f"📈 **Доходы**\n"
                f"├ 💸 Всего: {total_earned:,.0f} коинов\n"
                f"├ 🐻 От медведей: {daily_income * (datetime.utcnow() - user.created_at).days:,.0f} к\n"
                f"└ 👥 От рефералов: {(user.referral_earnings_tier1 or 0) + (user.referral_earnings_tier2 or 0) + (user.referral_earnings_tier3 or 0):,.0f} к\n\n"
                f"📉 **Расходы**\n"
                f"├ ❌ Всего: {total_spent:,.0f} коинов\n"
                f"└ 📊 Чистая прибыль: {profit:,.0f} к\n\n"
                f"⏰ **За периоды**\n"
                f"├ 📅 Сегодня: +{daily_income:,.0f} коинов\n"
                f"├ 🗓️ За неделю: {week_earnings:,.0f} к\n"
                f"└ 📆 Прогноз/месяц: {daily_income * 30:,.0f} к\n\n"
                f"💡 **Эффективность**\n"
                f"├ 📊 ROI: {(profit/total_spent*100) if total_spent > 0 else 0:.0f}%\n"
                f"└ 💵 Баланс: {user.coins:,.0f} коинов"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К статистике", callback_data="stats")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in stats_finance: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "stats_bears")
async def stats_bears(query: CallbackQuery):
    """
    Bears statistics.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            bears_query = select(Bear).where(Bear.owner_id == user.id).order_by(Bear.coins_per_hour.desc())
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if not bears:
                text = "🐻 **Статистика медведей**\n\nУ вас пока нет медведей!"
            else:
                total_income_hour = sum(b.coins_per_hour for b in bears)
                total_income_day = sum(b.coins_per_day for b in bears)
                avg_level = sum(b.level for b in bears) / len(bears)
                max_level = max(b.level for b in bears)
                
                # Count by type
                bears_by_type = {}
                for bear in bears:
                    bears_by_type[bear.bear_type] = bears_by_type.get(bear.bear_type, 0) + 1
                
                text = (
                    f"🐻 **Статистика медведей**\n\n"
                    f"📦 **Коллекция**\n"
                    f"├ Всего: {len(bears)}\n"
                    f"├ 📊 Ср. уровень: {avg_level:.1f}\n"
                    f"└ 🏆 Макс. уровень: {max_level}/{MAX_BEAR_LEVEL}\n\n"
                    f"💰 **Производительность**\n"
                    f"├ 💵 Доход/час: {total_income_hour:.1f} к\n"
                    f"├ 📅 Доход/день: {total_income_day:.1f} к\n"
                    f"└ 📆 Прогноз/месяц: {total_income_day * 30:,.0f} к\n\n"
                    f"🏆 **Топ-5 медведей**\n"
                )
                
                for idx, bear in enumerate(bears[:5], 1):
                    class_info = BEAR_CLASSES[bear.bear_type]
                    text += f"{idx}. {bear.name} (Lv{bear.level}) - {bear.coins_per_hour:.1f}к/ч\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К статистике", callback_data="stats")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in stats_bears: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "stats_cases")
async def stats_cases(query: CallbackQuery):
    """
    Cases statistics.
    """
    text = (
        f"🎁 **Статистика кейсов**\n\n"
        f"🚧 Функция в разработке!\n\n"
        f"Здесь будет:\n"
        f"• 📦 Количество открытых кейсов\n"
        f"• 🎯 Награды и дропы\n"
        f"• 📊 RTP (возврат)\n"
        f"• 🏆 Лучшие дропы\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К статистике", callback_data="stats")],
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    await query.answer()


@router.callback_query(F.data == "stats_referrals")
async def stats_referrals(query: CallbackQuery):
    """
    Referrals statistics.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Tier 1
            tier1_query = select(User).where(User.referred_by == user.telegram_id)
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            
            # Tier 2 count
            tier2_count = 0
            for t1 in tier1_users:
                t2_query = select(func.count(User.id)).where(User.referred_by == t1.telegram_id)
                t2_result = await session.execute(t2_query)
                tier2_count += t2_result.scalar() or 0
            
            total_earnings = (
                (user.referral_earnings_tier1 or 0) +
                (user.referral_earnings_tier2 or 0) +
                (user.referral_earnings_tier3 or 0)
            )
            
            text = (
                f"👥 **Реферальная статистика**\n\n"
                f"🌳 **Структура**\n"
                f"├ 🥇 1-й круг: {len(tier1_users)} чел (20%)\n"
                f"├ 🥈 2-й круг: {tier2_count} чел (10%)\n"
                f"└ 🥉 3-й круг: 0 чел (5%)\n\n"
                f"💰 **Доходы**\n"
                f"├ Tier 1: {user.referral_earnings_tier1 or 0:,.0f} к\n"
                f"├ Tier 2: {user.referral_earnings_tier2 or 0:,.0f} к\n"
                f"├ Tier 3: {user.referral_earnings_tier3 or 0:,.0f} к\n"
                f"└ 💸 Всего: {total_earnings:,.0f} коинов\n\n"
            )
            
            if tier1_users:
                text += f"🏆 **Топ рефералы**\n"
                for idx, ref in enumerate(tier1_users[:5], 1):
                    text += f"{idx}. @{ref.username or ref.first_name}\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Подробнее", callback_data="referrals")],
                [InlineKeyboardButton(text="⬅️ К статистике", callback_data="stats")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in stats_referrals: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "stats_achievements")
async def stats_achievements(query: CallbackQuery):
    """
    Achievements statistics.
    """
    text = (
        f"🏆 **Достижения**\n\n"
        f"🚧 Функция в разработке!\n\n"
        f"Здесь будут:\n"
        f"• ✅ Разблокированные\n"
        f"• 🔒 Заблокированные\n"
        f"• 🏆 Награды\n"
        f"• 📈 Прогресс\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К статистике", callback_data="stats")],
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    await query.answer()


@router.callback_query(F.data == "finance_stats")
async def finance_stats(query: CallbackQuery):
    """
    Show detailed finance statistics.
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get bears stats
            bears_query = select(Bear).where(Bear.owner_id == user.id)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            total_income_per_day = sum(bear.coins_per_day for bear in bears)
            
            # Get transaction stats for last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'earn',
                CoinTransaction.created_at >= week_ago
            )
            week_result = await session.execute(week_query)
            earned_week = week_result.scalar() or 0
            
            # Get total spent
            spent_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'spend'
            )
            spent_result = await session.execute(spent_query)
            total_spent = spent_result.scalar() or 0
            
            # Get total earned
            earned_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'earn'
            )
            earned_result = await session.execute(earned_query)
            total_earned = earned_result.scalar() or 0
            
            # Calculate profit
            total_profit = total_earned - total_spent
            
            text = (
                f"💰 **Финансовая статистика**\n\n"
                f"💼 **Текущий баланс**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {user.ton_balance:.4f}\n\n"
                f"💸 **Общая информация**\n"
                f"✅ Всего заработано: {total_earned:,.0f} коинов\n"
                f"❌ Всего потрачено: {total_spent:,.0f} коинов\n"
                f"📊 Чистый доход: {total_profit:,.0f} коинов\n\n"
                f"📈 **Ежедневный доход**\n"
                f"📅 От медведей: {total_income_per_day:.1f} коинов/день\n"
                f"🕐 За неделю: {earned_week:,.0f} коинов\n"
                f"📆 Прогноз в месяц: {total_income_per_day * 30:,.0f} коинов\n\n"
                f"💡 **Совет**\n"
                f"Купи больше медведей и улучши их уровни, чтобы увеличить доход!\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В профиль", callback_data="profile")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in finance_stats: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "settings")
async def settings_menu(query: CallbackQuery):
    """
    Show settings menu.
    """
    try:
        text = (
            f"⚙️ **Настройки**\n\n"
            f"📋 Здесь вы сможете настраивать свой аккаунт\n\n"
            f"🔧 **Доступные опции**:\n"
            f"• Язык интерфейса\n"
            f"• Уведомления\n"
            f"• Адрес кошелька\n"
            f"• Приватность\n\n"
            f"⏰ Скоро будут доступны!\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В профиль", callback_data="profile")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception as e:
            logger.warning(f"Could not edit message: {e}, sending new message instead")
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in settings_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
