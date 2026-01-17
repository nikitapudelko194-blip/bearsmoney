"""Analytics and tracking service."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User, Bear, CoinTransaction, Withdrawal

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for tracking and analyzing user behavior."""
    
    @staticmethod
    async def track_event(session: AsyncSession, user_id: int, event_type: str, metadata: Dict[str, Any] = None):
        """Track user event."""
        try:
            # TODO: Store events in a separate table for proper analytics
            logger.info(f"Event tracked: user={user_id}, type={event_type}, data={metadata}")
        except Exception as e:
            logger.error(f"Error tracking event: {e}", exc_info=True)
    
    @staticmethod
    async def get_daily_active_users(session: AsyncSession, days: int = 7) -> List[int]:
        """Get DAU for last N days."""
        try:
            result = []
            for i in range(days):
                day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                
                query = select(func.count(func.distinct(CoinTransaction.user_id))).where(
                    CoinTransaction.created_at >= day_start,
                    CoinTransaction.created_at < day_end
                )
                count_result = await session.execute(query)
                count = count_result.scalar() or 0
                result.append(count)
            
            return list(reversed(result))
        except Exception as e:
            logger.error(f"Error getting DAU: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def get_retention_cohort(session: AsyncSession, cohort_date: datetime) -> Dict[str, Any]:
        """Calculate retention for a specific cohort."""
        try:
            cohort_start = cohort_date.replace(hour=0, minute=0, second=0, microsecond=0)
            cohort_end = cohort_start + timedelta(days=1)
            
            # Users registered in cohort
            users_query = select(User).where(
                User.created_at >= cohort_start,
                User.created_at < cohort_end
            )
            users_result = await session.execute(users_query)
            cohort_users = users_result.scalars().all()
            cohort_size = len(cohort_users)
            
            if cohort_size == 0:
                return {"cohort_date": cohort_date, "size": 0, "retention": {}}
            
            user_ids = [u.id for u in cohort_users]
            
            # Calculate retention for days 1, 3, 7, 14, 30
            retention = {}
            for day in [1, 3, 7, 14, 30]:
                check_start = cohort_start + timedelta(days=day)
                check_end = check_start + timedelta(days=1)
                
                active_query = select(func.count(func.distinct(CoinTransaction.user_id))).where(
                    CoinTransaction.user_id.in_(user_ids),
                    CoinTransaction.created_at >= check_start,
                    CoinTransaction.created_at < check_end
                )
                active_result = await session.execute(active_query)
                active_count = active_result.scalar() or 0
                
                retention[f"day_{day}"] = round(active_count / cohort_size * 100, 2)
            
            return {
                "cohort_date": cohort_date,
                "size": cohort_size,
                "retention": retention
            }
        except Exception as e:
            logger.error(f"Error calculating retention: {e}", exc_info=True)
            return {"error": str(e)}
    
    @staticmethod
    async def get_revenue_metrics(session: AsyncSession) -> Dict[str, Any]:
        """Get revenue and monetization metrics."""
        try:
            # Total revenue (from premium, etc)
            # This is simplified - in production, track actual TON payments
            
            # Premium users
            premium_query = select(func.count(User.id)).where(User.is_premium == True)
            premium_result = await session.execute(premium_query)
            premium_count = premium_result.scalar() or 0
            
            # Total users
            total_query = select(func.count(User.id))
            total_result = await session.execute(total_query)
            total_users = total_result.scalar() or 0
            
            # Withdrawals
            withdrawals_query = select(func.sum(Withdrawal.amount_crypto)).where(
                Withdrawal.status == 'completed'
            )
            withdrawals_result = await session.execute(withdrawals_query)
            total_withdrawals = float(withdrawals_result.scalar() or 0)
            
            return {
                "premium_users": premium_count,
                "total_users": total_users,
                "premium_rate": round(premium_count / total_users * 100, 2) if total_users > 0 else 0,
                "total_withdrawals_ton": total_withdrawals,
            }
        except Exception as e:
            logger.error(f"Error getting revenue metrics: {e}", exc_info=True)
            return {"error": str(e)}
