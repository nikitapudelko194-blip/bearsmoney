"""Referral system service."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User, CoinTransaction
from datetime import datetime

logger = logging.getLogger(__name__)

# ПРОЦЕНТЫ КОМИССИИ ДЛЯ КАЖДОГО УРОВНЯ
REFERRAL_COMMISSION_TIER1 = 0.20  # 20% для 1-го круга
REFERRAL_COMMISSION_TIER2 = 0.10  # 10% для 2-го круга
REFERRAL_COMMISSION_TIER3 = 0.05  # 5% для 3-го круга


class ReferralService:
    """Service for referral system with 3-tier commissions."""
    
    @staticmethod
    async def process_referral_earnings(
        session: AsyncSession,
        user_id: int,
        amount_spent: float
    ) -> dict:
        """
        Process referral earnings when a user spends coins.
        
        3-Tier System:
        - Tier 1 (direct referrer): 20% of amount spent
        - Tier 2 (referrer's referrer): 10% of amount spent
        - Tier 3 (tier 2's referrer): 5% of amount spent
        
        Args:
            session: Database session
            user_id: ID of user who spent coins
            amount_spent: Amount of coins spent
        
        Returns:
            dict with earnings distributed to each tier
        """
        if amount_spent <= 0:
            return {'tier1': 0, 'tier2': 0, 'tier3': 0}
        
        earnings = {'tier1': 0, 'tier2': 0, 'tier3': 0}
        
        try:
            # Get user who spent coins
            user_query = select(User).where(User.id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user or not user.referred_by:
                # No referrer, nothing to do
                return earnings
            
            # ========== TIER 1: Direct referrer (20%) ==========
            tier1_referrer_query = select(User).where(User.telegram_id == user.referred_by)
            tier1_result = await session.execute(tier1_referrer_query)
            tier1_referrer = tier1_result.scalar_one_or_none()
            
            if tier1_referrer:
                tier1_earnings = amount_spent * REFERRAL_COMMISSION_TIER1
                tier1_referrer.coins += tier1_earnings
                tier1_referrer.referral_earnings_tier1 = (
                    (tier1_referrer.referral_earnings_tier1 or 0) + tier1_earnings
                )
                earnings['tier1'] = tier1_earnings
                
                # Log transaction
                transaction = CoinTransaction(
                    user_id=tier1_referrer.id,
                    amount=tier1_earnings,
                    transaction_type='referral_tier1',
                    description=f'Комиссия 20% от трат реферала ({amount_spent:.0f} коинов)'
                )
                session.add(transaction)
                
                logger.info(f"💰 Tier 1: User {tier1_referrer.id} earned {tier1_earnings:.2f} coins")
                
                # ========== TIER 2: Referrer's referrer (10%) ==========
                if tier1_referrer.referred_by:
                    tier2_referrer_query = select(User).where(
                        User.telegram_id == tier1_referrer.referred_by
                    )
                    tier2_result = await session.execute(tier2_referrer_query)
                    tier2_referrer = tier2_result.scalar_one_or_none()
                    
                    if tier2_referrer:
                        tier2_earnings = amount_spent * REFERRAL_COMMISSION_TIER2
                        tier2_referrer.coins += tier2_earnings
                        tier2_referrer.referral_earnings_tier2 = (
                            (tier2_referrer.referral_earnings_tier2 or 0) + tier2_earnings
                        )
                        earnings['tier2'] = tier2_earnings
                        
                        # Log transaction
                        transaction = CoinTransaction(
                            user_id=tier2_referrer.id,
                            amount=tier2_earnings,
                            transaction_type='referral_tier2',
                            description=f'Комиссия 10% от трат реферала 2-го круга ({amount_spent:.0f} коинов)'
                        )
                        session.add(transaction)
                        
                        logger.info(f"💰 Tier 2: User {tier2_referrer.id} earned {tier2_earnings:.2f} coins")
                        
                        # ========== TIER 3: Tier 2's referrer (5%) ==========
                        if tier2_referrer.referred_by:
                            tier3_referrer_query = select(User).where(
                                User.telegram_id == tier2_referrer.referred_by
                            )
                            tier3_result = await session.execute(tier3_referrer_query)
                            tier3_referrer = tier3_result.scalar_one_or_none()
                            
                            if tier3_referrer:
                                tier3_earnings = amount_spent * REFERRAL_COMMISSION_TIER3
                                tier3_referrer.coins += tier3_earnings
                                tier3_referrer.referral_earnings_tier3 = (
                                    (tier3_referrer.referral_earnings_tier3 or 0) + tier3_earnings
                                )
                                earnings['tier3'] = tier3_earnings
                                
                                # Log transaction
                                transaction = CoinTransaction(
                                    user_id=tier3_referrer.id,
                                    amount=tier3_earnings,
                                    transaction_type='referral_tier3',
                                    description=f'Комиссия 5% от трат реферала 3-го круга ({amount_spent:.0f} коинов)'
                                )
                                session.add(transaction)
                                
                                logger.info(f"💰 Tier 3: User {tier3_referrer.id} earned {tier3_earnings:.2f} coins")
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"❌ Error processing referral earnings: {e}", exc_info=True)
            await session.rollback()
        
        return earnings
    
    @staticmethod
    async def get_referral_stats(session: AsyncSession, user_id: int) -> dict:
        """
        Get referral statistics for a user.
        
        Returns:
            dict with referral counts and earnings for each tier
        """
        try:
            user_query = select(User).where(User.id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {}
            
            # Count tier 1 referrals (direct)
            tier1_query = select(User).where(User.referred_by == user.telegram_id)
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            
            # Count tier 2 referrals (referrals of tier 1)
            tier2_count = 0
            for t1_user in tier1_users:
                tier2_query = select(User).where(User.referred_by == t1_user.telegram_id)
                tier2_result = await session.execute(tier2_query)
                tier2_count += len(tier2_result.scalars().all())
            
            # Count tier 3 referrals (would need to iterate again)
            # For now, approximate or skip for performance
            
            return {
                'tier1_count': len(tier1_users),
                'tier2_count': tier2_count,
                'tier1_earnings': user.referral_earnings_tier1 or 0,
                'tier2_earnings': user.referral_earnings_tier2 or 0,
                'tier3_earnings': user.referral_earnings_tier3 or 0,
                'total_earnings': (
                    (user.referral_earnings_tier1 or 0) +
                    (user.referral_earnings_tier2 or 0) +
                    (user.referral_earnings_tier3 or 0)
                )
            }
        except Exception as e:
            logger.error(f"❌ Error getting referral stats: {e}", exc_info=True)
            return {}
