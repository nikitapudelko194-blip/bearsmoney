"""Interactive onboarding tutorial handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

TUTORIAL_REWARD = 500  # Coins for completing tutorial


@router.callback_query(F.data == "tutorial")
async def tutorial_start(query: CallbackQuery):
    """Start interactive tutorial."""
    try:
        text = (
            "👋 **Добро пожаловать в BearsMoney!**\n\n"
            "🐻 Я помогу тебе разобраться в игре.\n\n"
            "🎯 **Ты узнаешь:**\n"
            "• Как покупать медведей\n"
            "• Как зарабатывать Coins\n"
            "• Как обменивать на TON\n"
            "• Как приглашать друзей\n\n"
            f"🎁 **Награда:** {TUTORIAL_REWARD:,} Coins\n"
            f"⏱️ **Время:** 2 минуты\n\n"
            "🚀 Начнём?"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Начать обучение", callback_data="tutorial_step_1")],
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="main_menu")]
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in tutorial_start: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "tutorial_step_1")
async def tutorial_step_1(query: CallbackQuery):
    """Tutorial step 1: Bears."""
    text = (
        "🐻 **Шаг 1: Медведи**\n\n"
        "🌟 Медведи - твои работники!\n\n"
        "📊 **Редкость:**\n"
        "🟩 Common - 1 к/ч\n"
        "🟦 Rare - 5 к/ч\n"
        "🟪 Epic - 20 к/ч\n"
        "🟧 Legendary - 100 к/ч\n\n"
        "💰 Купи медведей в магазине!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Далее", callback_data="tutorial_step_2")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="tutorial")]
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    await query.answer()


@router.callback_query(F.data == "tutorial_step_2")
async def tutorial_step_2(query: CallbackQuery):
    """Tutorial step 2: Earning."""
    text = (
        "🪙 **Шаг 2: Заработок**\n\n"
        "⏰ Медведи зарабатывают Coins автоматически!\n\n"
        "💡 **Способы заработка:**\n"
        "• 🐻 Медведи (пассивный доход)\n"
        "• 🎁 Ежедневные награды\n"
        "• 🎰 Колесо фортуны\n"
        "• 📺 Просмотр рекламы\n"
        "• 👥 Рефералы (20% с друзей)\n\n"
        "💪 Чем больше медведей, тем больше Coins!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Далее", callback_data="tutorial_step_3")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="tutorial_step_1")]
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    await query.answer()


@router.callback_query(F.data == "tutorial_step_3")
async def tutorial_step_3(query: CallbackQuery):
    """Tutorial step 3: Exchange."""
    text = (
        "💱 **Шаг 3: Обмен**\n\n"
        "💎 Обменивай Coins на TON!\n\n"
        "📈 **Курс:**\n"
        "1 TON = 500,000 Coins\n"
        "1 Coin = 0.00000200 TON\n\n"
        "📉 **Комиссия:** 2%\n\n"
        "💸 Можно обменивать в обе стороны:\n"
        "• Coins → TON\n"
        "• TON → Coins\n\n"
        "💼 Вывод TON на кошелёк доступен!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Далее", callback_data="tutorial_step_4")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="tutorial_step_2")]
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    await query.answer()


@router.callback_query(F.data == "tutorial_step_4")
async def tutorial_step_4(query: CallbackQuery):
    """Tutorial step 4: Referrals."""
    text = (
        "👥 **Шаг 4: Рефералы**\n\n"
        "🚀 Приглашай друзей и зарабатывай!\n\n"
        "💰 **Вознаграждение:**\n"
        "• 20% с дохода друга (1-й круг)\n"
        "• 10% со 2-го круга\n"
        "• 5% с 3-го круга\n\n"
        "🎁 **Бонус:**\n"
        "+ 500 Coins за каждого друга\n\n"
        "🔗 Твоя реферальная ссылка в разделе '👥 Рефералы'!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить", callback_data="tutorial_complete")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="tutorial_step_3")]
    ])
    
    try:
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
    except Exception:
        await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
    
    await query.answer()


@router.callback_query(F.data == "tutorial_complete")
async def tutorial_complete(query: CallbackQuery):
    """Complete tutorial and give reward."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Give reward
            user.coins += TUTORIAL_REWARD
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=TUTORIAL_REWARD,
                transaction_type='tutorial_reward',
                description=f'Награда за прохождение обучения'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                "🎉 **Обучение завершено!**\n\n"
                f"🎁 Ты получил: {TUTORIAL_REWARD:,} Coins\n"
                f"💼 Новый баланс: {user.coins:,.0f} Coins\n\n"
                "🚀 **Теперь ты готов:**\n"
                "✅ Покупать медведей\n"
                "✅ Зарабатывать Coins\n"
                "✅ Обменивать на TON\n"
                "✅ Приглашать друзей\n\n"
                "💪 Удачи в игре!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 В магазин", callback_data="shop")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 Поздравляем!")
            
            logger.info(f"✅ User {user.telegram_id} completed tutorial and got {TUTORIAL_REWARD} coins")
    
    except Exception as e:
        logger.error(f"❌ Error in tutorial_complete: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
