"""Economy service for managing coins, bears, and earnings."""
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database.models import User, Bear, CoinTransaction
from config import settings

logger = logging.getLogger(__name__)


class EconomyService:
    """Service for economy calculations."""
    
    BEAR_COSTS = {
        'common': 100,
        'rare': 500,
        'epic': 2000,
        'legendary': 5000,
    }
    
    BEAR_HOURLY_INCOME = {
        'common': 1.0,
        'rare': 5.0,
        'epic': 25.0,
        'legendary': 100.0,
    }
    
    @staticmethod
    async def calculate_coins_earned(session: AsyncSession, user_id: int) -> float:
        """Calculate total coins earned since last claim."""
        # Get all user's bears
        query = select(Bear).where(Bear.owner_id == user_id)
        result = await session.execute(query)
        bears = result.scalars().all()
        
        total_coins = 0.0
        now = datetime.utcnow()
        
        for bear in bears:
            # Calculate coins based on time passed and boost
            coins_per_hour = bear.coins_per_hour * bear.boost_multiplier
            
            # If boost expired, reset multiplier
            if bear.boost_until and bear.boost_until < now:
                bear.boost_multiplier = 1.0
                bear.boost_until = None
            
            total_coins += coins_per_hour  # Simplified: coins per hour
        
        return total_coins
    
    @staticmethod
    async def buy_bear(
        session: AsyncSession,
        user_id: int,
        bear_type: str
    ) -> bool:
        """Buy a bear for the user."""
        if bear_type not in EconomyService.BEAR_COSTS:
            logger.error(f"Invalid bear type: {bear_type}")
            return False
        
        cost = EconomyService.BEAR_COSTS[bear_type]
        
        # Get user
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user or user.coins < cost:
            logger.warning(f"User {user_id} has insufficient coins to buy {bear_type}")
            return False
        
        # Deduct coins
        user.coins -= cost
        
        # Create bear
        new_bear = Bear(
            owner_id=user_id,
            bear_type=bear_type,
            coins_per_hour=EconomyService.BEAR_HOURLY_INCOME[bear_type],
            coins_per_day=EconomyService.BEAR_HOURLY_INCOME[bear_type] * 24,
        )
        session.add(new_bear)
        
        # Log transaction
        transaction = CoinTransaction(
            user_id=user_id,
            amount=-cost,
            transaction_type='spend',
            description=f'Bought {bear_type} bear'
        )
        session.add(transaction)
        
        await session.commit()
        logger.info(f"User {user_id} bought {bear_type} bear")
        return True
    
    @staticmethod
    async def upgrade_bear(
        session: AsyncSession,
        bear_id: int,
        upgrade_type: str = 'level'
    ) -> bool:
        """Upgrade a bear."""
        query = select(Bear).where(Bear.id == bear_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            return False
        
        if upgrade_type == 'level':
            upgrade_cost = bear.level * 50
            bear.level += 1
            bear.coins_per_hour *= 1.2
            bear.coins_per_day = bear.coins_per_hour * 24
        else:
            return False
        
        # Deduct coins from user
        query = select(User).where(User.id == bear.owner_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user or user.coins < upgrade_cost:
            return False
        
        user.coins -= upgrade_cost
        
        # Log transaction
        transaction = CoinTransaction(
            user_id=user.id,
            amount=-upgrade_cost,
            transaction_type='spend',
            description=f'Upgraded bear #{bear_id} to level {bear.level}'
        )
        session.add(transaction)
        
        await session.commit()
        logger.info(f"Bear {bear_id} upgraded to level {bear.level}")
        return True
    
    @staticmethod
    async def apply_boost(
        session: AsyncSession,
        bear_id: int,
        multiplier: float = 2.0,
        hours: int = 24
    ) -> bool:
        """Apply a boost to a bear."""
        query = select(Bear).where(Bear.id == bear_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            return False
        
        bear.boost_multiplier = multiplier
        bear.boost_until = datetime.utcnow() + timedelta(hours=hours)
        
        await session.commit()
        logger.info(f"Applied {multiplier}x boost to bear {bear_id} for {hours} hours")
        return True
    
    @staticmethod
    async def calculate_withdrawal(
        session: AsyncSession,
        user_id: int,
        coin_amount: float
    ) -> float:
        """Calculate TON amount after commission."""
        # Get user to check for subscription discounts
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return 0
        
        # Base commission
        commission = coin_amount * settings.WITHDRAW_COMMISSION
        
        # Apply subscription discount if user has premium
        if user.is_premium:
            from app.database.models import Subscription
            query = select(Subscription).where(
                (Subscription.user_id == user_id) &
                (Subscription.status == 'active')
            )
            result = await session.execute(query)
            sub = result.scalar_one_or_none()
            if sub:
                commission *= (1 - sub.commission_reduction)
        
        # Calculate TON amount
        ton_amount = (coin_amount - commission) * settings.COIN_TO_TON_RATE
        return ton_amount
