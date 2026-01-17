"""Push notifications service."""
import logging
from datetime import datetime, timedelta
from typing import List
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User, Bear

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending push notifications."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_daily_reminder(self, session: AsyncSession):
        """Send daily login reminder to users."""
        try:
            # Get users who haven't logged in today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            query = select(User).where(
                User.updated_at < today_start
            ).limit(100)  # Process in batches
            
            result = await session.execute(query)
            users = result.scalars().all()
            
            for user in users:
                try:
                    await self.bot.send_message(
                        user.telegram_id,
                        "🔥 Не забудь зайти сегодня!\n\n"
                        "└ 🎁 Ежедневная награда ждёт тебя!\n"
                        "└ 🎰 Крути колесо фортуны!\n"
                        "└ 💰 Собери доход от медведей!"
                    )
                except Exception as e:
                    logger.debug(f"Could not send notification to {user.telegram_id}: {e}")
            
            logger.info(f"Sent daily reminders to {len(users)} users")
        except Exception as e:
            logger.error(f"Error sending daily reminders: {e}", exc_info=True)
    
    async def send_collection_reminder(self, session: AsyncSession, user_id: int, coins_available: float):
        """Send reminder to collect coins."""
        try:
            user_query = select(User).where(User.id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                return
            
            await self.bot.send_message(
                user.telegram_id,
                f"💰 **Пора собирать монеты!**\n\n"
                f"Твои медведи накопили:\n"
                f"└ 🪙 {coins_available:,.0f} Coins\n\n"
                f"Заходи в игру и забери их!"
            )
            logger.info(f"Sent collection reminder to user {user.telegram_id}")
        except Exception as e:
            logger.error(f"Error sending collection reminder: {e}", exc_info=True)
    
    async def send_event_notification(self, user_ids: List[int], title: str, message: str):
        """Send event notification to multiple users."""
        try:
            success = 0
            for telegram_id in user_ids:
                try:
                    await self.bot.send_message(
                        telegram_id,
                        f"🎉 **{title}**\n\n{message}"
                    )
                    success += 1
                except Exception as e:
                    logger.debug(f"Could not send event notification to {telegram_id}: {e}")
            
            logger.info(f"Sent event notifications to {success}/{len(user_ids)} users")
        except Exception as e:
            logger.error(f"Error sending event notifications: {e}", exc_info=True)
