"""Start command handler."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User
from datetime import datetime
from app.keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Start command handler.
    """
    try:
        async with get_session() as session:
            # Check if user exists
            query = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                # Create new user
                user = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    coins=100.0,  # Start with 100 coins
                    created_at=datetime.utcnow(),
                )
                session.add(user)
                await session.commit()
                
                welcome_text = (
                    f"🐻 **Лавы в БеарсМани!**\n\n"
                    f"🎉 Привет, {message.from_user.first_name}!\n\n"
                    f"🪣 К вам в этом приложении вы можете:\n"
                    f"- 🐻 Набомавать медведей\n"
                    f"- 💰 Зарабатывать коины\n"
                    f"- 🎁 Открывать ящики\n"
                    f"- 📋 Выполнять квесты\n"
                    f"- 👥 Приглашать друзей\n\n"
                    f"🌟 Вы получили 100 коинов для начала!\n\n"
                    f"🙋 Начните с покупки первого медведя!"
                )
                logger.info(f"🐻 New user registered: {message.from_user.id} ({message.from_user.first_name})")
            else:
                # User already exists
                welcome_text = (
                    f"🐻 **Лавы в БеарсМани!**\n\n"
                    f"💰 **Основное меню**\n\n"
                    f"👤 @{message.from_user.username or 'User'}\n"
                    f"💰 Васы: {user.coins:.0f} коинов\n"
                    f"🤝 Уровень: {user.level}"
                )
                logger.info(f"🐻 User returned: {message.from_user.id}")
            
            await message.answer(
                welcome_text,
                reply_markup=get_main_menu(),
                parse_mode="markdown"
            )
            
            # Remove any old reply keyboards
            await message.answer(
                "🐻 Меню загружено!",
                reply_markup=ReplyKeyboardRemove()
            )
            
    except Exception as e:
        logger.error(f"❌ Error in cmd_start: {e}", exc_info=True)
        await message.answer(
            f"❌ Ощибка при инициализации.\n\n"
            f"Технические детали: {str(e)}"
        )
