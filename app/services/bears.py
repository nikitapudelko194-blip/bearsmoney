"""Service for managing bears."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Bear, User
from datetime import datetime, timedelta
import random

BEAR_TYPES = {
    'common': {'cost': 100, 'income_per_hour': 1.0, 'emoji': '🐻️'},
    'rare': {'cost': 500, 'income_per_hour': 3.0, 'emoji': '🐻'},
    'epic': {'cost': 2000, 'income_per_hour': 8.0, 'emoji': '🐈'},
    'legendary': {'cost': 10000, 'income_per_hour': 20.0, 'emoji': '🐆'},
}


class BearsService:
    """Service for managing bears."""
    
    @staticmethod
    async def get_user_bears(session: AsyncSession, user_id: int) -> list[Bear]:
        """
        Get all bears for a user.
        """
        query = select(Bear).where(Bear.owner_id == user_id)
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def create_bear(
        session: AsyncSession,
        user_id: int,
        bear_type: str,
        name: str = None
    ) -> Bear:
        """
        Create a new bear for user.
        """
        if bear_type not in BEAR_TYPES:
            raise ValueError(f"Invalid bear type: {bear_type}")
        
        bear_info = BEAR_TYPES[bear_type]
        bear = Bear(
            owner_id=user_id,
            bear_type=bear_type,
            name=name or f"{bear_type.capitalize()} #{random.randint(1000, 9999)}",
            coins_per_hour=bear_info['income_per_hour'],
            coins_per_day=bear_info['income_per_hour'] * 24,
        )
        session.add(bear)
        await session.commit()
        return bear
    
    @staticmethod
    async def upgrade_bear(session: AsyncSession, bear_id: int, user_id: int) -> Bear:
        """
        Upgrade a bear to the next level.
        Costs 50 coins per level.
        """
        query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            raise ValueError("Bear not found")
        
        upgrade_cost = 50 * bear.level
        user_query = select(User).where(User.id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        if user.coins < upgrade_cost:
            raise ValueError("Not enough coins")
        
        # Upgrade bear
        bear.level += 1
        bear.coins_per_hour = bear.coins_per_hour * 1.2
        bear.coins_per_day = bear.coins_per_day * 1.2
        user.coins -= upgrade_cost
        
        await session.commit()
        return bear
    
    @staticmethod
    async def apply_boost(session: AsyncSession, bear_id: int, user_id: int, hours: int) -> Bear:
        """
        Apply a boost to a bear (increase income temporarily).
        """
        query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            raise ValueError("Bear not found")
        
        bear.boost_multiplier = 2.0
        bear.boost_until = datetime.utcnow() + timedelta(hours=hours)
        
        await session.commit()
        return bear
    
    @staticmethod
    async def get_bear_income(bear: Bear) -> float:
        """
        Calculate current income for a bear (with boosts).
        """
        income = bear.coins_per_hour
        
        # Apply boost if active
        if bear.boost_until and bear.boost_until > datetime.utcnow():
            income *= bear.boost_multiplier
        
        return income
    
    @staticmethod
    async def format_bear_info(bear: Bear, user: User) -> str:
        """
        Format bear info for display.
        """
        emoji = BEAR_TYPES[bear.bear_type]['emoji']
        boost_info = ""
        
        if bear.boost_until and bear.boost_until > datetime.utcnow():
            time_left = bear.boost_until - datetime.utcnow()
            hours = time_left.total_seconds() // 3600
            minutes = (time_left.total_seconds() % 3600) // 60
            boost_info = f"\n🔥 Буст активен: {int(hours)}ч {int(minutes)}м (x{bear.boost_multiplier})"
        
        return (
            f"{emoji} **{bear.name}**\n"
            f"Тип: {bear.bear_type}\n"
            f"Уровень: {bear.level}\n"
            f"Доход: {bear.coins_per_hour:.1f} коинов/час\n"
            f"Доход в день: {bear.coins_per_day:.1f} коинов\n"
            f"Куплен: {bear.purchased_at.strftime('%d.%m.%Y')}"
            f"{boost_info}"
        )
    
    @staticmethod
    async def sell_bear(session: AsyncSession, bear_id: int, user_id: int) -> float:
        """
        Sell a bear and get 50% of its cost.
        """
        query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            raise ValueError("Bear not found")
        
        bear_cost = BEAR_TYPES[bear.bear_type]['cost']
        refund = bear_cost * 0.5
        
        # Update user coins
        user_query = select(User).where(User.id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        user.coins += refund
        
        # Delete bear
        await session.delete(bear)
        await session.commit()
        
        return refund
    
    @staticmethod
    async def rename_bear(session: AsyncSession, bear_id: int, user_id: int, new_name: str) -> Bear:
        """
        Rename a bear.
        """
        query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            raise ValueError("Bear not found")
        
        if len(new_name) > 50:
            raise ValueError("Name too long")
        
        bear.name = new_name
        await session.commit()
        return bear
