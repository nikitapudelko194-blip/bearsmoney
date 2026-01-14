"""Handlers for user profile."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.db import get_session
from app.database.models import User, Bear, CoinTransaction
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
                    return f"\n💳 **Премиум активен** ({days}д {hours}ч)"
                else:
                    return f"\n💳 **Премиум активен** ({hours}ч)"
        return "\n💳 **Премиум активен** (бессрочно)"
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
            
            # Format text
            text = (
                f"👤 **Профиль {query.from_user.first_name}**\n\n"
                f"📊 **Основная информация**\n"
                f"🆔 ID: `{user.telegram_id}`\n"
                f"👤 @{query.from_user.username or 'не указано'}\n"
                f"⭐ Уровень: {user.level}\n"
                f"{format_premium_status(user)}\n\n"
                f"💰 **Финансы**\n"
                f"🪙 Баланс: {user.coins:.0f} коинов\n"
                f"💸 Всего заработано: {total_earned:.0f} коинов\n\n"
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
                f"📅 **Аккаунт**\n"
                f"📝 Создан: {user.created_at.strftime('%d.%m.%Y')}\n"
                f"🔄 Обновлен: {user.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            # Add referral info if exists
            if user.referred_count > 0:
                text += f"\n👥 **Рефереалы**\n"
                text += f"👤 Приглашено: {user.referred_count} чел.\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
                [InlineKeyboardButton(text="💰 Финансы", callback_data="finance_stats")],
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in show_profile: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


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
                f"💸 **Общая информация**\n"
                f"🪙 Текущий баланс: {user.coins:.0f} коинов\n"
                f"✅ Всего заработано: {total_earned:.0f} коинов\n"
                f"❌ Всего потрачено: {total_spent:.0f} коинов\n"
                f"📊 Чистый доход: {total_profit:.0f} коинов\n\n"
                f"📈 **Ежедневный доход**\n"
                f"📅 От медведей: {total_income_per_day:.1f} коинов/день\n"
                f"🕐 За неделю: {earned_week:.0f} коинов\n"
                f"📆 Прогноз в месяц: {total_income_per_day * 30:.0f} коинов\n\n"
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
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
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
            f"📝 Здесь вы сможете настраивать свой аккаунт\n\n"
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
