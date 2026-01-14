"""Start command and user registration handler."""
import logging
from aiogram import Router, F
from aiogram.types import Message, User as TelegramUser
from aiogram.filters import Command
from sqlalchemy import select
from app.database.db import AsyncSessionLocal
from app.database.models import User
from app.keyboards.main_menu import get_main_keyboard
from app.texts.messages import WELCOME_MESSAGE, ALREADY_REGISTERED

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, user: TelegramUser | None = None):
    """Handle /start command - register or show main menu."""
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    first_name = message.from_user.first_name or "User"
    
    async with AsyncSessionLocal() as session:
        # Check if user exists
        query = select(User).where(User.telegram_id == user_id)
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # User already registered
            await message.answer(
                ALREADY_REGISTERED.format(name=first_name),
                reply_markup=get_main_keyboard()
            )
            logger.info(f"User {user_id} ({username}) already registered")
            return
        
        # Register new user
        new_user = User(
            telegram_id=user_id,
            username=username,
            first_name=first_name,
            coins=100,  # Starting bonus
        )
        session.add(new_user)
        await session.commit()
        
        logger.info(f"New user registered: {user_id} ({username})")
        
        # Send welcome message
        await message.answer(
            WELCOME_MESSAGE.format(
                name=first_name,
                coins=100
            ),
            reply_markup=get_main_keyboard()
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = """
🐻 **БеарсМани - Помощь**

**Основные команды:**
/start - Начать или вернуться в главное меню
/profile - Мой профиль и статистика
/bears - Мои медведи
/shop - Магазин медведей и улучшений
/wallet - Кошелёк и вывод
/quests - Квесты и задания
/referral - Реферальная программа
/admin - Админ-панель (только для администратора)
/help - Эта помощь

**Основная механика:**
🐻 Каждый медведь приносит коины
💰 Накапливай коины и покупай новых медведей
⬆️ Улучшай медведей для увеличения дохода
🔄 Обменивай коины на криптовалюту TON

Для подробной информации используй кнопки меню.
    """
    await message.answer(help_text, parse_mode="Markdown")
