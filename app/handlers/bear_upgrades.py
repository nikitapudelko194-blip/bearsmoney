"""Bear upgrades and evolution handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Bear, CoinTransaction
from app.services.bears import BEAR_CLASSES, MAX_BEAR_LEVEL

logger = logging.getLogger(__name__)
router = Router()

# Upgrade costs
UPGRADE_COST = 1000  # coins per upgrade
UPGRADE_BONUS = 0.1  # +10% income

# Evolution requirements
EVOLUTION_REQUIREMENTS = {
    "common_to_rare": {"count": 10, "cost": 5000, "type": "common"},
    "rare_to_epic": {"count": 10, "cost": 50000, "type": "rare"},
    "epic_to_legendary": {"count": 10, "cost": 500000, "type": "epic"},
}


@router.callback_query(F.data == "bear_upgrades")
async def bear_upgrades_menu(query: CallbackQuery):
    """Show bear upgrades menu."""
    try:
        text = (
            "🔧 **Улучшение медведей**\n\n"
            "Здесь вы можете улучшить своих медведей!\n\n"
            "💡 **Доступные опции:**\n\n"
            "🔝 **Апгрейд**\n"
            f"├ Стоимость: {UPGRADE_COST:,} Coins\n"
            f"├ Бонус: +{int(UPGRADE_BONUS * 100)}% к доходу\n"
            "└ Можно улучшать бесконечно\n\n"
            "🔄 **Эволюция**\n"
            "├ 10 Common → 1 Rare (5,000 к)\n"
            "├ 10 Rare → 1 Epic (50,000 к)\n"
            "├ 10 Epic → 1 Legendary (500,000 к)\n"
            "└ Медведи сжигаются безвозвратно\n\n"
            "⚡ **Навыки** (скоро)\n"
            "└ 2x coins на 1 час\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔝 Улучшить медведя", callback_data="upgrade_bear_list")],
            [InlineKeyboardButton(text="🔄 Эволюция", callback_data="evolution_menu")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="bears")]
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in bear_upgrades_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "upgrade_bear_list")
async def upgrade_bear_list(query: CallbackQuery):
    """Show list of bears to upgrade."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            bears_query = select(Bear).where(Bear.owner_id == user.id).order_by(Bear.coins_per_hour.desc()).limit(10)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if not bears:
                text = "🐻 У вас пока нет медведей для улучшения!"
                keyboard = [[InlineKeyboardButton(text="🛒 В магазин", callback_data="shop")]]
            else:
                text = (
                    f"🔝 **Выберите медведя для улучшения**\n\n"
                    f"💰 Стоимость: {UPGRADE_COST:,} Coins\n"
                    f"📈 Эффект: +{int(UPGRADE_BONUS * 100)}% к доходу\n\n"
                    f"💼 Ваш баланс: {user.coins:,.0f} Coins\n\n"
                )
                
                keyboard = []
                for bear in bears:
                    class_info = BEAR_CLASSES[bear.bear_type]
                    new_income = bear.coins_per_hour * (1 + UPGRADE_BONUS)
                    keyboard.append([InlineKeyboardButton(
                        text=f"{class_info['color']} {bear.name} (Lv{bear.level}) - {bear.coins_per_hour:.1f}→{new_income:.1f}к/ч",
                        callback_data=f"upgrade_bear_{bear.id}"
                    )])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bear_upgrades")])
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in upgrade_bear_list: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("upgrade_bear_"))
async def upgrade_bear_confirm(query: CallbackQuery):
    """Confirm bear upgrade."""
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
                await query.answer("❌ Медведь не найден", show_alert=True)
                return
            
            if user.coins < UPGRADE_COST:
                await query.answer(
                    f"❌ Недостаточно Coins\n\nНужно: {UPGRADE_COST:,}\nУ вас: {user.coins:,.0f}",
                    show_alert=True
                )
                return
            
            # Upgrade bear
            old_income = bear.coins_per_hour
            bear.coins_per_hour *= (1 + UPGRADE_BONUS)
            bear.coins_per_day = bear.coins_per_hour * 24
            bear.level = min(bear.level + 1, MAX_BEAR_LEVEL)
            
            # Deduct cost
            user.coins -= UPGRADE_COST
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-UPGRADE_COST,
                transaction_type='bear_upgrade',
                description=f'Улучшение {bear.name} до уровня {bear.level}'
            )
            session.add(transaction)
            
            await session.commit()
            
            class_info = BEAR_CLASSES[bear.bear_type]
            
            text = (
                "✅ **Медведь улучшен!**\n\n"
                f"🐻 {class_info['color']} **{bear.name}**\n"
                f"⬆️ Уровень: {bear.level - 1} → {bear.level}\n"
                f"📈 Доход: {old_income:.1f} → {bear.coins_per_hour:.1f} к/ч\n"
                f"📊 Прирост: +{int(UPGRADE_BONUS * 100)}%\n\n"
                f"💼 Новый баланс: {user.coins:,.0f} Coins"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔝 Улучшить ещё", callback_data="upgrade_bear_list")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="bear_upgrades")]
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 Медведь улучшен!")
            
            logger.info(f"✅ User {user.telegram_id} upgraded bear {bear.id} to level {bear.level}")
    
    except Exception as e:
        logger.error(f"❌ Error in upgrade_bear_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "evolution_menu")
async def evolution_menu(query: CallbackQuery):
    """Show evolution menu."""
    try:
        text = (
            "🔄 **Эволюция медведей**\n\n"
            "Объедините несколько медведей одного типа\nв одного более редкого!\n\n"
            "📋 **Рецепты:**\n\n"
            "🟩 **10 Common → 1 Rare**\n"
            "├ Стоимость: 5,000 Coins\n"
            "└ Получите случайного Rare\n\n"
            "🟦 **10 Rare → 1 Epic**\n"
            "├ Стоимость: 50,000 Coins\n"
            "└ Получите случайного Epic\n\n"
            "🟪 **10 Epic → 1 Legendary**\n"
            "├ Стоимость: 500,000 Coins\n"
            "└ Получите случайного Legendary\n\n"
            "⚠️ **Важно:** Исходные медведи будут сожжены!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟩→🟦 Common → Rare", callback_data="evolve_common_rare")],
            [InlineKeyboardButton(text="🟦→🟪 Rare → Epic", callback_data="evolve_rare_epic")],
            [InlineKeyboardButton(text="🟪→🟧 Epic → Legendary", callback_data="evolve_epic_legendary")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="bear_upgrades")]
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in evolution_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
