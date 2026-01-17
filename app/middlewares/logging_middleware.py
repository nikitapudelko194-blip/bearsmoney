"""Logging middleware for tracking user actions."""
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging user actions."""
    
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        """
        Log user action before processing.
        """
        if isinstance(event, Message):
            logger.info(
                f"💬 Message from @{event.from_user.username} ({event.from_user.id}): {event.text[:50] if event.text else 'N/A'}"
            )
        elif isinstance(event, CallbackQuery):
            logger.info(
                f"👉 Callback from @{event.from_user.username} ({event.from_user.id}): {event.data}"
            )
        
        # Process request
        return await handler(event, data)
