"""Onboarding tutorial system."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

TUTORIAL_REWARD = 500  # Coins for completing tutorial


@router.callback_query(F.data == "tutorial")
async def show_tutorial(query: CallbackQuery):
    """Show tutorial overview with start button."""
    try:
        text = (
            "📚 **Краткое обучение Bears Money**\n\n"
            "🐻 **Медведи** - твои питомцы!\n"
            "• Каждый медведь приносит Coins каждый час\n"
            "• Есть 4 редкости: Common, Rare, Epic, Legendary\n"
            "• Чем выше редкость - тем сильнее медведь\n\n"
            "🎮 **Чем заняться?**\n"
            "• 🐻 Собирай и прокачивай медведей\n"
            "• 🎁 Получай ежедневные награды\n"
            "• 👥 Приглашай друзей (бонусы за рефералов)\n"
            "• 📺 Смотри рекламу за Coins\n"
            "• ⚔️ Участвуй в PvP битвах\n\n"
            "💎 **Premium подписка**\n"
            "• Получай эксклюзивные бонусы\n"
            "• Ускоряй прогресс\n"
            "• Создавай NFT из своих медведей\n\n"
            "🎯 **Главная цель**\n"
            "Собери лучшую коллекцию медведей и побеждай в PvP битвах!\n\n"
            "💡 Нажми 'Начать игру' чтобы начать!\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Начать игру!", callback_data="main_menu")],
            [InlineKeyboardButton(text="📖 Подробное обучение", callback_data="tutorial_step_1")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in show_tutorial: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# Tutorial steps
TUTORIAL_STEPS = [
    {
        "step": 1,
        "title": "👋 Добро пожаловать!",
        "text": (
            "Привет! 🐻\n\n"
            "Я помогу тебе разобраться в Bears Money!\n\n"
            "🎮 **Что это?**\n"
            "Bears Money - это Telegram игра, где ты:\n"
            "• Собираешь коллекцию медведей\n"
            "• Прокачиваешь их силу\n"
            "• Сражаешься с другими игроками\n"
            "• Соревнуешься с друзьями\n\n"
            "💡 Нажми 'Далее', чтобы продолжить!"
        ),
    },
    {
        "step": 2,
        "title": "🐻 Медведи",
        "text": (
            "🐻 **Медведи - твои питомцы!**\n\n"
            "Каждый медведь приносит Coins каждый час!\n\n"
            "🎯 **Редкости:**\n"
            "• Common (обычные) - 1 к/ч\n"
            "• Rare (редкие) - 5 к/ч\n"
            "• Epic (эпические) - 15 к/ч\n"
            "• Legendary (легендарные) - 50 к/ч\n\n"
            "🔝 **Как получить?**\n"
            "• Открывай кейсы\n"
            "• Покупай в магазине\n"
            "• Получай за рефералов"
        ),
    },
    {
        "step": 3,
        "title": "💰 Игровая валюта",
        "text": (
            "💰 **Как получать Coins?**\n\n"
            "🐻 **Медведи**\n"
            "Автоматический доход каждый час!\n\n"
            "🎁 **Ежедневные награды**\n"
            "Заходи каждый день и получай бонусы!\n\n"
            "👥 **Рефералы**\n"
            "Приглашай друзей и получай % с их дохода!\n\n"
            "📺 **Реклама**\n"
            "Смотри рекламу = получай коины!\n\n"
            "⚔️ **PvP батлы**\n"
            "Соревнуйся с другими и выигрывай!"
        ),
    },
    {
        "step": 4,
        "title": "⭐ Premium подписка",
        "text": (
            "⭐ **Premium - ускорь свой прогресс!**\n\n"
            "💎 **Преимущества Premium:**\n"
            "• +50% к доходу от медведей\n"
            "• 0% комиссии в магазине\n"
            "• Эксклюзивные кейсы\n"
            "• Premium бейдж в профиле\n"
            "• Приоритетная поддержка\n\n"
            "🖼️ **NFT медведи**\n"
            "Создавай уникальных NFT медведей!\n"
            "Коллекционируй редкие экземпляры!"
        ),
    },
    {
        "step": 5,
        "title": "🎆 Поздравляем!",
        "text": (
            "🎆 **Ты прошел обучение!**\n\n"
            f"🎁 Награда: {TUTORIAL_REWARD} Coins\n\n"
            "💡 **Советы:**\n"
            "• Заходи каждый день за наградами\n"
            "• Улучшай медведей для PvP\n"
            "• Приглашай друзей - получай бонусы\n"
            "• Участвуй в событиях\n\n"
            "🚀 Удачи в игре!"
        ),
    },
]


@router.callback_query(F.data == "start_tutorial")
async def start_tutorial(query: CallbackQuery):
    """Start tutorial."""
    await show_tutorial_step(query, 1)


@router.callback_query(F.data.startswith("tutorial_step_"))
async def tutorial_step(query: CallbackQuery):
    """Show tutorial step."""
    step = int(query.data.split("_")[-1])
    await show_tutorial_step(query, step)


async def show_tutorial_step(query: CallbackQuery, step: int):
    """Show specific tutorial step."""
    try:
        step_data = next((s for s in TUTORIAL_STEPS if s["step"] == step), None)
        
        if not step_data:
            await query.answer("❌ Шаг не найден!", show_alert=True)
            return
        
        text = (
            f"**{step_data['title']}**\n"
            f"(Шаг {step}/{len(TUTORIAL_STEPS)})\n\n"
            f"{step_data['text']}"
        )
        
        keyboard = []
        
        # Add navigation buttons
        nav_buttons = []
        if step > 1:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"tutorial_step_{step-1}"))
        
        if step < len(TUTORIAL_STEPS):
            nav_buttons.append(InlineKeyboardButton(text="➡️ Далее", callback_data=f"tutorial_step_{step+1}"))
        else:
            nav_buttons.append(InlineKeyboardButton(text="✅ Завершить", callback_data="complete_tutorial"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton(text="❌ Пропустить", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        try:
            await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in show_tutorial_step: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "complete_tutorial")
async def complete_tutorial(query: CallbackQuery):
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
                description='Награда за прохождение обучения'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"🎉 **Поздравляем!**\n\n"
                f"Ты успешно прошел обучение!\n\n"
                f"🎁 Награда: +{TUTORIAL_REWARD} Coins\n"
                f"💼 Новый баланс: {user.coins:,.0f} Coins\n\n"
                f"🚀 Теперь ты готов к игре!\n"
                f"💡 Начни с покупки первого медведя!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ В магазин", callback_data="shop")],
                [InlineKeyboardButton(text="🎮 В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 +500 Coins!")
            logger.info(f"✅ User {user.telegram_id} completed tutorial")
    
    except Exception as e:
        logger.error(f"❌ Error in complete_tutorial: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
