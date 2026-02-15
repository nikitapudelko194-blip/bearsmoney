"""Analytics and tracking system."""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.models import User, Bear, CoinTransaction

logger = logging.getLogger(__name__)


class Analytics:
    """Analytics service for tracking events and metrics."""
    
    @staticmethod
    async def track_event(session: AsyncSession, user_id: int, event_name: str, properties: dict = None):
        """
        Track user event.
        
        Args:
            session: Database session
            user_id: User ID
            event_name: Event name (e.g., 'bear_purchased', 'case_opened')
            properties: Additional event properties
        """
        try:
            # TODO: Save to analytics table or send to external service
            logger.info(f"📊 Event tracked: {event_name} for user {user_id}, props: {properties}")
        except Exception as e:
            logger.error(f"❌ Error tracking event: {e}")
    
    @staticmethod
    async def get_user_lifetime_value(session: AsyncSession, user_id: int) -> float:
        """
        Calculate user lifetime value (LTV).
        """
        try:
            # Get total TON spent
            ton_spent_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user_id,
                CoinTransaction.transaction_type.in_(['premium_purchase', 'nft_mint'])
            )
            result = await session.execute(ton_spent_query)
            ton_spent = result.scalar() or 0
            
            return float(ton_spent)
        except Exception as e:
            logger.error(f"❌ Error calculating LTV: {e}")
            return 0.0
    
    @staticmethod
    async def get_retention_rate(session: AsyncSession, days: int = 7) -> float:
        """
        Calculate retention rate.
        """
        try:
            # TODO: Implement retention calculation
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error calculating retention: {e}")
            return 0.0
    
    @staticmethod
    async def get_daily_active_users(session: AsyncSession) -> int:
        """
        Get daily active users count.
        """
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            query = select(func.count(User.id.distinct())).where(
                User.updated_at >= today_start
            )
            result = await session.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"❌ Error getting DAU: {e}")
            return 0
    
    @staticmethod
    async def get_conversion_rate(session: AsyncSession) -> float:
        """
        Calculate free-to-paid conversion rate.
        """
        try:
            # Total users
            total_query = select(func.count(User.id))
            total_result = await session.execute(total_query)
            total_users = total_result.scalar() or 0
            
            # Paid users
            paid_query = select(func.count(User.id)).where(User.is_premium == True)
            paid_result = await session.execute(paid_query)
            paid_users = paid_result.scalar() or 0
            
            if total_users == 0:
                return 0.0
            
            return (paid_users / total_users) * 100
        except Exception as e:
            logger.error(f"❌ Error calculating conversion: {e}")
            return 0.0


# Singleton instance
analytics = Analytics()
