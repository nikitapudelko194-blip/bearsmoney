"""Utility decorators for bot handlers."""
import logging
from functools import wraps
from aiogram.types import Message
from sqlalchemy import select
from app.database.db import AsyncSessionLocal
from app.database.models import User
from config import settings

logger = logging.getLogger(__name__)


def admin_only(func):
    """
    Decorator to restrict command to admin only.
    """
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id != settings.ADMIN_ID:
            await message.answer(
                "❌ **Доступ запрещен!** Эта команда доступна только администратору.",
                parse_mode="Markdown"
            )
            logger.warning(f"Unauthorized admin command attempt by {message.from_user.id}")
            return
        return await func(message, *args, **kwargs)
    return wrapper


def require_registration(func):
    """
    Decorator to check if user is registered.
    """
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        
        async with AsyncSessionLocal() as session:
            query = select(User).where(User.telegram_id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(
                "👋 Ты еще не зарегистрирован! Напиши /start для начала.",
                parse_mode="Markdown"
            )
            return
        
        # Pass user to handler
        kwargs['user'] = user
        return await func(message, *args, **kwargs)
    return wrapper


def rate_limit(calls_per_minute: int = 5):
    """
    Decorator to rate limit commands.
    
    Args:
        calls_per_minute: Maximum calls allowed per minute
    """
    def decorator(func):
        user_calls = {}
        
        @wraps(func)
        async def wrapper(message: Message, *args, **kwargs):
            import time
            
            user_id = message.from_user.id
            current_time = time.time()
            
            if user_id not in user_calls:
                user_calls[user_id] = []
            
            # Remove old calls (older than 1 minute)
            user_calls[user_id] = [
                call_time for call_time in user_calls[user_id]
                if current_time - call_time < 60
            ]
            
            if len(user_calls[user_id]) >= calls_per_minute:
                await message.answer(
                    f"⏱️ Слишком много запросов! Подождите минуту перед следующим запросом."
                )
                return
            
            user_calls[user_id].append(current_time)
            return await func(message, *args, **kwargs)
        
        return wrapper
    return decorator


def log_command(func):
    """
    Decorator to log command usage.
    """
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        logger.info(
            f"Command {func.__name__} called by user {message.from_user.id} "
            f"(@{message.from_user.username})"
        )
        try:
            return await func(message, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            await message.answer(
                "❌ Произошла ошибка. Пожалуйста, попробуйте позже."
            )
    return wrapper
