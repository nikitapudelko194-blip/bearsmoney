"""PvP battles system."""
import logging
import random
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.db import get_session
from app.database.models import User, Bear, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

# PvP ranks
PVP_RANKS = [
    {"name": "🥉 Bronze", "min_rating": 0, "max_rating": 999},
    {"name": "🥈 Silver", "min_rating": 1000, "max_rating": 1999},
    {"name": "🥇 Gold", "min_rating": 2000, "max_rating": 2999},
    {"name": "💎 Platinum", "min_rating": 3000, "max_rating": 3999},
    {"name": "👑 Diamond", "min_rating": 4000, "max_rating": 4999},
    {"name": "🏆 Legend", "min_rating": 5000, "max_rating": 999999},
]

# Bear power calculation
BEAR_TYPE_POWER = {
    "common": 1.0,
    "rare": 1.5,
    "epic": 2.0,
    "legendary": 3.0,
}


def calculate_bear_power(bear: Bear) -> float:
    """Calculate bear battle power."""
    base_power = BEAR_TYPE_POWER.get(bear.bear_type, 1.0)
    level_bonus = bear.level * 0.1
    return (base_power + level_bonus) * 100


def get_user_rank(rating: int) -> str:
    """Get rank by rating."""
    for rank in PVP_RANKS:
        if rank["min_rating"] <= rating <= rank["max_rating"]:
            return rank["name"]
    return PVP_RANKS[0]["name"]


@router.callback_query(F.data == "pvp")
async def pvp_menu(query: CallbackQuery):
    """Show PvP menu."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get user bears
            bears_query = select(Bear).where(Bear.owner_id == user.id)
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if not bears:
                await query.answer("❌ У вас нет медведей для батлов!", show_alert=True)
                return
            
            # Get PvP stats (mock for now)
            pvp_rating = 1000  # TODO: Add PvPStats model
            pvp_wins = 0
            pvp_losses = 0
            
            rank = get_user_rank(pvp_rating)
            
            # Calculate total power
            total_power = sum(calculate_bear_power(bear) for bear in bears)
            
            text = (
                f"⚔️ **PvP Арена**\n\n"
                f"🏅 **Ваш ранг:** {rank}\n"
                f"⭐ Рейтинг: {pvp_rating}\n"
                f"💪 Сила медведей: {total_power:.0f}\n\n"
                f"📊 **Статистика:**\n"
                f"├ ✅ Побед: {pvp_wins}\n"
                f"├ ❌ Поражений: {pvp_losses}\n"
                f"└ 📈 Винрейт: {(pvp_wins/(pvp_wins+pvp_losses)*100) if (pvp_wins+pvp_losses) > 0 else 0:.1f}%\n\n"
                f"🎮 **Режимы:**\n"
                f"• Быстрый бой (100 коинов ставка)\n"
                f"• Рейтинговый бой (изменение ранга)\n"
                f"• Турнир (недельные призы)\n\n"
                f"💡 Выберите противника:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚡ Быстрый бой", callback_data="pvp_quick")],
                [InlineKeyboardButton(text="🏆 Рейтинговый бой", callback_data="pvp_ranked")],
                [InlineKeyboardButton(text="🎯 Найти противника", callback_data="pvp_matchmaking")],
                [InlineKeyboardButton(text="📊 Топ-100", callback_data="pvp_leaderboard")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in pvp_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "pvp_quick")
async def pvp_quick_battle(query: CallbackQuery):
    """Start quick PvP battle."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check balance
            bet_amount = 100
            if user.coins < bet_amount:
                await query.answer(f"❌ Недостаточно коинов! Нужно: {bet_amount}", show_alert=True)
                return
            
            # Get user's best bear
            bears_query = select(Bear).where(Bear.owner_id == user.id).order_by(Bear.level.desc())
            bears_result = await session.execute(bears_query)
            user_bears = bears_result.scalars().all()
            
            if not user_bears:
                await query.answer("❌ У вас нет медведей!", show_alert=True)
                return
            
            user_bear = user_bears[0]
            user_power = calculate_bear_power(user_bear)
            
            # Find opponent (random bear from other users)
            opponent_query = select(Bear).where(Bear.owner_id != user.id).order_by(func.random()).limit(1)
            opponent_result = await session.execute(opponent_query)
            opponent_bear = opponent_result.scalar_one_or_none()
            
            if not opponent_bear:
                await query.answer("❌ Не найден противник!", show_alert=True)
                return
            
            opponent_power = calculate_bear_power(opponent_bear)
            
            # Calculate win chance
            total_power = user_power + opponent_power
            win_chance = user_power / total_power
            
            # Battle simulation
            user_wins = random.random() < win_chance
            
            # Update balances
            if user_wins:
                user.coins += bet_amount
                reward = bet_amount * 2
                result_text = "🎉 **ПОБЕДА!**"
                result_emoji = "✅"
            else:
                user.coins -= bet_amount
                reward = 0
                result_text = "😢 **ПОРАЖЕНИЕ!**"
                result_emoji = "❌"
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=reward - bet_amount,
                transaction_type='pvp_battle',
                description=f'PvP бой: {"Победа" if user_wins else "Поражение"}'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"⚔️ **Результаты боя**\n\n"
                f"{result_text}\n\n"
                f"🐻 **Ваш медведь:**\n"
                f"{user_bear.name} (Lv{user_bear.level})\n"
                f"💪 Сила: {user_power:.0f}\n\n"
                f"🐻 **Противник:**\n"
                f"{opponent_bear.name} (Lv{opponent_bear.level})\n"
                f"💪 Сила: {opponent_power:.0f}\n\n"
                f"🎲 **Шанс победы:** {win_chance*100:.1f}%\n\n"
                f"{result_emoji} **Итог:**\n"
            )
            
            if user_wins:
                text += f"💰 Награда: +{reward} коинов\n"
            else:
                text += f"💸 Потеря: -{bet_amount} коинов\n"
            
            text += f"\n💼 Новый баланс: {user.coins:,.0f} Coins"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Еще бой", callback_data="pvp_quick")],
                [InlineKeyboardButton(text="⬅️ К PvP", callback_data="pvp")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer(f"{result_emoji} {'Победа!' if user_wins else 'Поражение!'}")
    
    except Exception as e:
        logger.error(f"❌ Error in pvp_quick_battle: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
