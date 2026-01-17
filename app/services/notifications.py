"""Push notifications service."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Bot
from sqlalchemy import select
from app.database.models import User, Bear
from config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending push notifications to users."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_notification(
        self,
        telegram_id: int,
        message: str,
        parse_mode: str = "markdown"
    ) -> bool:
        """Send notification to user."""
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"✅ Notification sent to user {telegram_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error sending notification to {telegram_id}: {e}")
            return False
    
    async def notify_daily_reward(self, telegram_id: int, streak_days: int):
        """Notify user about available daily reward."""
        message = (
            f"🎉 **Ежедневная награда готова!**\n\n"
            f"🔥 Текущая серия: {streak_days} дней\n\n"
            f"🎁 Зайди в бот, чтобы забрать!"
        )
        return await self.send_notification(telegram_id, message)
    
    async def notify_coins_ready(self, telegram_id: int, coins_amount: float):
        """Notify user that coins are ready to collect."""
        message = (
            f"🪙 **Монеты готовы!**\n\n"
            f"🐻 Ваши медведи назаработали {coins_amount:,.0f} Coins!\n\n"
            f"💰 Зайди в бот, чтобы забрать!"
        )
        return await self.send_notification(telegram_id, message)
    
    async def notify_premium_expiring(self, telegram_id: int, days_left: int):
        """Notify user that premium subscription is expiring."""
        message = (
            f"⚠️ **Premium подписка заканчивается!**\n\n"
            f"⏰ Осталось: {days_left} дней\n\n"
            f"⭐ Продли сейчас, чтобы не потерять бонусы!"
        )
        return await self.send_notification(telegram_id, message)
    
    async def notify_event_started(self, telegram_id: int, event_name: str):
        """Notify user about new event."""
        message = (
            f"🎉 **Новое событие!**\n\n"
            f"🎯 {event_name}\n\n"
            f"🎁 Зайди в бот, чтобы узнать подробности!"
        )
        return await self.send_notification(telegram_id, message)


# Global notification service
notification_service: Optional[NotificationService] = None


async def init_notification_service(bot: Bot):
    """Initialize notification service."""
    global notification_service
    notification_service = NotificationService(bot)
    logger.info("✅ Notification service initialized")


async def get_notification_service() -> NotificationService:
    """Get notification service instance."""
    if notification_service is None:
        raise RuntimeError("Notification service not initialized")
    return notification_service
