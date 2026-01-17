"""Analytics service for tracking user events and behavior."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select, func
from app.database.models import User, CoinTransaction, Bear

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Analytics service for tracking and analyzing user behavior."""
    
    def __init__(self, session):
        self.session = session
    
    async def track_event(self, user_id: int, event_name: str, properties: Optional[Dict] = None):
        """Track user event."""
        try:
            # Log event
            logger.info(f"📊 Event: {event_name} - User: {user_id} - Props: {properties}")
            
            # In production: Send to analytics platform (Amplitude, Mixpanel, etc.)
            # await self._send_to_analytics_platform(user_id, event_name, properties)
            
        except Exception as e:
            logger.error(f"❌ Error tracking event: {e}", exc_info=True)
    
    async def get_retention_rate(self, days: int = 7) -> Dict:
        """Calculate user retention rate."""
        try:
            now = datetime.utcnow()
            start_date = now - timedelta(days=days)
            
            # Get total users registered in period
            total_query = select(func.count(User.id)).where(
                User.created_at >= start_date
            )
            total_result = await self.session.execute(total_query)
            total_users = total_result.scalar() or 0
            
            if total_users == 0:
                return {"retention_rate": 0, "total_users": 0, "active_users": 0}
            
            # Get active users (users who made transactions in last 24h)
            active_date = now - timedelta(days=1)
            active_query = select(func.count(func.distinct(CoinTransaction.user_id))).where(
                CoinTransaction.created_at >= active_date
            )
            active_result = await self.session.execute(active_query)
            active_users = active_result.scalar() or 0
            
            retention_rate = (active_users / total_users) * 100 if total_users > 0 else 0
            
            return {
                "retention_rate": round(retention_rate, 2),
                "total_users": total_users,
                "active_users": active_users,
                "period_days": days
            }
        
        except Exception as e:
            logger.error(f"❌ Error calculating retention: {e}", exc_info=True)
            return {"retention_rate": 0, "total_users": 0, "active_users": 0}
    
    async def get_user_ltv(self, user_id: int) -> float:
        """Calculate user lifetime value."""
        try:
            # Get total spent
            spent_query = select(func.sum(CoinTransaction.amount)).where(
                CoinTransaction.user_id == user_id,
                CoinTransaction.transaction_type == 'spend'
            )
            spent_result = await self.session.execute(spent_query)
            total_spent = abs(spent_result.scalar() or 0)
            
            # In production: Calculate based on real money spent
            # For now, use coins as proxy (1000 coins = $1)
            ltv = total_spent / 1000
            
            return round(ltv, 2)
        
        except Exception as e:
            logger.error(f"❌ Error calculating LTV: {e}", exc_info=True)
            return 0.0
    
    async def get_cohort_analysis(self, cohort_days: int = 30) -> List[Dict]:
        """Perform cohort analysis."""
        try:
            now = datetime.utcnow()
            cohorts = []
            
            for i in range(cohort_days):
                cohort_date = now - timedelta(days=i)
                cohort_start = cohort_date.replace(hour=0, minute=0, second=0, microsecond=0)
                cohort_end = cohort_start + timedelta(days=1)
                
                # Get users registered in this cohort
                cohort_query = select(func.count(User.id)).where(
                    User.created_at >= cohort_start,
                    User.created_at < cohort_end
                )
                cohort_result = await self.session.execute(cohort_query)
                cohort_size = cohort_result.scalar() or 0
                
                cohorts.append({
                    "date": cohort_start.strftime("%Y-%m-%d"),
                    "users": cohort_size,
                    "day": i
                })
            
            return cohorts
        
        except Exception as e:
            logger.error(f"❌ Error in cohort analysis: {e}", exc_info=True)
            return []


# Global analytics instance
analytics = None


async def get_analytics(session):
    """Get analytics service instance."""
    return AnalyticsService(session)
