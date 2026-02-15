"""Push notifications system."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Bot

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending push notifications."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_daily_reward_reminder(self, user_telegram_id: int):
        """
        Send reminder about daily reward.
        """
        try:
            text = (
                "🎁 **Не забудь забрать ежедневную награду!**\n\n"
                "Твоя серия может оборваться, если ты не зайдешь сегодня! 🔥"
            )
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=text,
                parse_mode="markdown"
            )
            logger.info(f"✅ Sent daily reward reminder to user {user_telegram_id}")
        except Exception as e:
            logger.error(f"❌ Error sending daily reward reminder: {e}")
    
    async def send_coins_ready_notification(self, user_telegram_id: int, amount: float):
        """
        Notify user that coins are ready to collect.
        """
        try:
            text = (
                f"💰 **Медведи назаработали коины!**\n\n"
                f"Забери {amount:,.0f} Coins прямо сейчас! 🐻"
            )
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=text,
                parse_mode="markdown"
            )
            logger.info(f"✅ Sent coins ready notification to user {user_telegram_id}")
        except Exception as e:
            logger.error(f"❌ Error sending coins notification: {e}")
    
    async def send_premium_expiring_notification(self, user_telegram_id: int, hours_left: int):
        """
        Notify user that premium is expiring soon.
        """
        try:
            text = (
                f"⚠️ **Premium истекает!**\n\n"
                f"Твоя подписка закончится через {hours_left} часов.\n"
                "Продли сейчас, чтобы не потерять бонусы! 🌟"
            )
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=text,
                parse_mode="markdown"
            )
            logger.info(f"✅ Sent premium expiring notification to user {user_telegram_id}")
        except Exception as e:
            logger.error(f"❌ Error sending premium expiring notification: {e}")
    
    async def send_event_notification(self, user_telegram_id: int, event_title: str, event_description: str):
        """
        Send notification about special event.
        """
        try:
            text = (
                f"🎉 **{event_title}**\n\n"
                f"{event_description}"
            )
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=text,
                parse_mode="markdown"
            )
            logger.info(f"✅ Sent event notification to user {user_telegram_id}: {event_title}")
        except Exception as e:
            logger.error(f"❌ Error sending event notification: {e}")
