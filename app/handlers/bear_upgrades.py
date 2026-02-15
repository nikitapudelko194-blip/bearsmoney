"""Bear upgrade system."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Bear, CoinTransaction
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = Router()

# Upgrade costs
UPGRADE_COSTS = {
    "boost_income": 1000,  # +10% income for 24h
    "skill_2x": 5000,      # 2x coins for 1 hour
    "evolution": 10000,     # Evolve to next tier
}

# Evolution paths
EVOLUTION_PATHS = {
    "common": "rare",
    "rare": "epic",
    "epic": "legendary",
    "legendary": None,  # Max tier
}


@router.callback_query(F.data.startswith("upgrade_bear_"))
async def upgrade_bear_menu(query: CallbackQuery):
    """Show bear upgrade menu."""
    try:
        bear_id = int(query.data.split("_")[-1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one_or_none()
            
            if not bear:
                await query.answer("❌ Медведь не найден!", show_alert=True)
                return
            
            can_evolve = EVOLUTION_PATHS.get(bear.bear_type) is not None
            has_boost = bear.boost_until and bear.boost_until > datetime.utcnow()
            
            text = (
                f"🔧 **Улучшение медведя**\n\n"
                f"🐻 {bear.name}\n"
                f"⭐ Уровень: {bear.level}\n"
                f"💰 Доход: {bear.coins_per_hour:.1f} к/ч\n"
                f"🎨 Тип: {bear.bear_type}\n\n"
            )
            
            if has_boost:
                boost_time_left = bear.boost_until - datetime.utcnow()
                hours = boost_time_left.total_seconds() / 3600
                text += f"⚡ Активный буст: {bear.boost_multiplier:.1f}x ({hours:.1f}ч)\n\n"
            
            text += (
                f"🛠 **Доступные улучшения:**\n\n"
                f"💪 **Усиление дохода** ({UPGRADE_COSTS['boost_income']} к)\n"
                f"• +10% дохода на 24 часа\n\n"
                f"⚡ **Супер-скилл** ({UPGRADE_COSTS['skill_2x']} к)\n"
                f"• 2x коины на 1 час\n\n"
            )
            
            if can_evolve:
                next_tier = EVOLUTION_PATHS[bear.bear_type]
                text += (
                    f"🌟 **Эволюция** ({UPGRADE_COSTS['evolution']} к)\n"
                    f"• Превратить в {next_tier}\n"
                    f"• +50% дохода навсегда\n\n"
                )
            
            text += f"💼 Ваш баланс: {user.coins:,.0f} Coins"
            
            keyboard = []
            keyboard.append([InlineKeyboardButton(text="💪 Усилить доход", callback_data=f"do_upgrade_boost_{bear_id}")])
            keyboard.append([InlineKeyboardButton(text="⚡ Супер-скилл", callback_data=f"do_upgrade_skill_{bear_id}")])
            
            if can_evolve:
                keyboard.append([InlineKeyboardButton(text="🌟 Эволюция", callback_data=f"do_upgrade_evolve_{bear_id}")])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bear_info_{bear_id}")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in upgrade_bear_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("do_upgrade_boost_"))
async def do_upgrade_boost(query: CallbackQuery):
    """Apply income boost."""
    try:
        bear_id = int(query.data.split("_")[-1])
        cost = UPGRADE_COSTS["boost_income"]
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.coins < cost:
                await query.answer(f"❌ Недостаточно коинов! Нужно: {cost}", show_alert=True)
                return
            
            bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one()
            
            # Deduct coins
            user.coins -= cost
            
            # Apply boost
            bear.boost_multiplier = 1.1
            bear.boost_until = datetime.utcnow() + timedelta(hours=24)
            bear.coins_per_hour *= 1.1
            bear.coins_per_day *= 1.1
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-cost,
                transaction_type='upgrade',
                description=f'Усиление дохода медведя {bear.name}'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"✅ **Улучшение применено!**\n\n"
                f"🐻 {bear.name}\n"
                f"💪 Буст: +10% дохода\n"
                f"⏰ Действует: 24 часа\n\n"
                f"💰 Новый доход: {bear.coins_per_hour:.1f} к/ч\n"
                f"💼 Новый баланс: {user.coins:,.0f} Coins"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Другие улучшения", callback_data=f"upgrade_bear_{bear_id}")],
                [InlineKeyboardButton(text="⬅️ К медведю", callback_data=f"bear_info_{bear_id}")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Буст активирован!")
            logger.info(f"✅ User {user.telegram_id} boosted bear {bear_id}")
    
    except Exception as e:
        logger.error(f"❌ Error in do_upgrade_boost: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("do_upgrade_evolve_"))
async def do_upgrade_evolve(query: CallbackQuery):
    """Evolve bear to next tier."""
    try:
        bear_id = int(query.data.split("_")[-1])
        cost = UPGRADE_COSTS["evolution"]
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.coins < cost:
                await query.answer(f"❌ Недостаточно коинов! Нужно: {cost}", show_alert=True)
                return
            
            bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one()
            
            next_tier = EVOLUTION_PATHS.get(bear.bear_type)
            if not next_tier:
                await query.answer("❌ Это максимальный уровень!", show_alert=True)
                return
            
            # Deduct coins
            user.coins -= cost
            
            # Evolve
            old_type = bear.bear_type
            bear.bear_type = next_tier
            bear.coins_per_hour *= 1.5
            bear.coins_per_day *= 1.5
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-cost,
                transaction_type='evolution',
                description=f'Эволюция медведя {bear.name}: {old_type} → {next_tier}'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"🌟 **ЭВОЛЮЦИЯ ЗАВЕРШЕНА!**\n\n"
                f"🐻 {bear.name}\n"
                f"✨ {old_type} → {next_tier}\n\n"
                f"💰 Новый доход: {bear.coins_per_hour:.1f} к/ч\n"
                f"📈 Увеличение: +50%\n\n"
                f"💼 Новый баланс: {user.coins:,.0f} Coins"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🌟 Эволюция успешна!")
            logger.info(f"✅ User {user.telegram_id} evolved bear {bear_id}: {old_type} → {next_tier}")
    
    except Exception as e:
        logger.error(f"❌ Error in do_upgrade_evolve: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
