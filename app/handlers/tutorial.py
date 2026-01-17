"""Onboarding and tutorial handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

TUTORIAL_REWARD = 500  # 500 coins for completing tutorial

TUTORIAL_STEPS = [
    {
        "title": "Добро пожаловать!",
        "text": (
            "🐻 **Добро пожаловать в Bears Money!**\n\n"
            "Это игра, где вы можете:\n"
            "├ 🐻 Собирать медведей\n"
            "├ 💰 Зарабатывать монеты\n"
            "├ 💎 Обменивать на TON\n"
            "└ 🎁 Получать награды\n\n"
            "Давайте начнём обучение!"
        ),
        "button": "▶️ Начать"
    },
    {
        "title": "Медведи",
        "text": (
            "🐻 **Медведи - основа игры**\n\n"
            "Каждый медведь приносит монеты:\n"
            "├ ⚪ Common: 10-50 к/час\n"
            "├ 🔵 Rare: 50-150 к/час\n"
            "├ 🟣 Epic: 150-500 к/час\n"
            "└ 🟠 Legendary: 500-2000 к/час\n\n"
            "Покупайте кейсы для получения медведей!"
        ),
        "button": "▶️ Далее"
    },
    {
        "title": "Заработок",
        "text": (
            "💰 **Как зарабатывать?**\n\n"
            "1️⃣ Медведи автоматически добывают монеты\n"
            "2️⃣ Собирайте ежедневные награды\n"
            "3️⃣ Крутите колесо фортуны\n"
            "4️⃣ Приглашайте друзей (реферальная программа)\n"
            "5️⃣ Смотрите рекламу\n\n"
            "💡 Чем больше медведей, тем выше доход!"
        ),
        "button": "▶️ Далее"
    },
    {
        "title": "Обмен TON",
        "text": (
            "💎 **Обмен на TON**\n\n"
            "Монеты можно обменять на TON:\n"
            "├ 📊 Курс: ~10,000 Coins = 1 TON\n"
            "├ 💸 Комиссия: 2% (Premium: 1%, VIP: 0%)\n"
            "└ ⚡ Вывод: мгновенный\n\n"
            "🏦 Минимальная сумма: 0.01 TON\n\n"
            "💡 Покупайте Premium для выгодных условий!"
        ),
        "button": "▶️ Далее"
    },
    {
        "title": "Готово!",
        "text": (
            "🎉 **Обучение завершено!**\n\n"
            "Вы получаете:\n"
            "└ 💰 500 Coins!\n\n"
            "📚 **Полезные советы:**\n"
            "├ Заходите каждый день за наградами\n"
            "├ Улучшайте медведей до макс. уровня\n"
            "├ Приглашайте друзей (20% от их дохода!)\n"
            "└ Участвуйте в PvP битвах\n\n"
            "🚀 Удачи в игре!"
        ),
        "button": "🎁 Забрать награду"
    }
]


@router.callback_query(F.data == "tutorial")
async def tutorial_start(query: CallbackQuery):
    """Start tutorial."""
    await show_tutorial_step(query, 0)


@router.callback_query(F.data.startswith("tutorial_step_"))
async def tutorial_step(query: CallbackQuery):
    """Show tutorial step."""
    step = int(query.data.split("_")[-1])
    await show_tutorial_step(query, step)


async def show_tutorial_step(query: CallbackQuery, step: int):
    """Show specific tutorial step."""
    try:
        if step >= len(TUTORIAL_STEPS):
            # Completed - give reward
            await tutorial_complete(query)
            return
        
        step_data = TUTORIAL_STEPS[step]
        
        text = f"📚 **Обучение ({step + 1}/{len(TUTORIAL_STEPS)})**\n\n{step_data['text']}"
        
        keyboard = []
        
        if step < len(TUTORIAL_STEPS) - 1:
            keyboard.append([InlineKeyboardButton(
                text=step_data['button'],
                callback_data=f"tutorial_step_{step + 1}"
            )])
        else:
            # Last step
            keyboard.append([InlineKeyboardButton(
                text=step_data['button'],
                callback_data="tutorial_complete"
            )])
        
        if step > 0:
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"tutorial_step_{step - 1}")])
        
        keyboard.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        try:
            await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"Error in show_tutorial_step: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "tutorial_complete")
async def tutorial_complete(query: CallbackQuery):
    """Complete tutorial and give reward."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check if already completed
            check_query = select(CoinTransaction).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'tutorial_reward'
            )
            check_result = await session.execute(check_query)
            existing = check_result.scalar_one_or_none()
            
            if existing:
                await query.answer("✅ Вы уже прошли обучение!", show_alert=True)
                return
            
            # Give reward
            user.coins += TUTORIAL_REWARD
            
            transaction = CoinTransaction(
                user_id=user.id,
                amount=TUTORIAL_REWARD,
                transaction_type='tutorial_reward',
                description='Награда за обучение'
            )
            session.add(transaction)
            await session.commit()
            
            text = (
                f"🎉 **Обучение завершено!**\n\n"
                f"✅ Награда получена:\n"
                f"└ 💰 +{TUTORIAL_REWARD} Coins\n\n"
                f"💼 Ваш баланс: {user.coins:,.0f} Coins\n\n"
                f"🚀 Теперь вы готовы к игре!\n\n"
                f"💡 **Что делать дальше?**\n"
                f"├ 🎁 Открыть кейс и получить первого медведя\n"
                f"├ 🔥 Собрать ежедневную награду\n"
                f"├ 👥 Пригласить друга\n"
                f"└ ⭐ Купить Premium подписку"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Открыть кейс", callback_data="cases")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 Награда получена!")
            logger.info(f"User {user.telegram_id} completed tutorial, earned {TUTORIAL_REWARD} coins")
    except Exception as e:
        logger.error(f"Error in tutorial_complete: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
