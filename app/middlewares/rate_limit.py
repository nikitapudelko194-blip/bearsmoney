"""Rate limiting middleware to prevent spam."""
import logging
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

# Rate limit settings
RATE_LIMIT_SECONDS = 1  # 1 request per second
MAX_REQUESTS_PER_MINUTE = 30  # Max 30 requests per minute

# Storage for rate limiting
user_last_request: Dict[int, datetime] = {}
user_request_count: Dict[int, list] = {}


class RateLimitMiddleware(BaseMiddleware):
    """Middleware for rate limiting user requests."""
    
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        """
        Rate limit check before processing request.
        """
        # Get user ID
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)
        
        now = datetime.utcnow()
        
        # Check requests per second
        last_request = user_last_request.get(user_id)
        if last_request:
            time_diff = (now - last_request).total_seconds()
            if time_diff < RATE_LIMIT_SECONDS:
                logger.warning(f"⚠️ Rate limit (per second) exceeded for user {user_id}")
                if isinstance(event, CallbackQuery):
                    await event.answer("⏰ Слишком частые запросы. Подождите...", show_alert=True)
                return
        
        # Check requests per minute
        if user_id not in user_request_count:
            user_request_count[user_id] = []
        
        # Clean old requests (older than 1 minute)
        user_request_count[user_id] = [
            req_time for req_time in user_request_count[user_id]
            if (now - req_time).total_seconds() < 60
        ]
        
        # Check if limit exceeded
        if len(user_request_count[user_id]) >= MAX_REQUESTS_PER_MINUTE:
            logger.warning(f"⚠️ Rate limit (per minute) exceeded for user {user_id}")
            if isinstance(event, CallbackQuery):
                await event.answer(
                    "⚠️ Слишком много запросов!\n\nПодождите 1 минуту.",
                    show_alert=True
                )
            return
        
        # Update rate limit data
        user_last_request[user_id] = now
        user_request_count[user_id].append(now)
        
        # Process request
        return await handler(event, data)
