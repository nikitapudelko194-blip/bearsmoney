"""Service for managing bears."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Bear, User
from datetime import datetime, timedelta
import random

# Bear classification system with 10 variants per rarity class
BEAR_CLASSES = {
    'common': {
        'name': '🐻 Обычные',
        'emoji': '🐻️',
        'cost': 100,
        'income_per_hour_base': 1.0,
        'rarity': 'Обычный',
        'color': '⚪',  # Белый
        'sell_price': 50,  # 50% от стоимости
        'require_premium': False,
        'variants': 10,  # 10 различных медведей
    },
    'rare': {
        'name': '🟢 Редкие',
        'emoji': '🐻',
        'cost': 500,
        'income_per_hour_base': 3.0,
        'rarity': 'Редкий',
        'color': '🟢',  # Зелёный
        'sell_price': 250,
        'require_premium': False,
        'variants': 10,
    },
    'epic': {
        'name': '🟣 Эпические',
        'emoji': '🐨',
        'cost': 2000,
        'income_per_hour_base': 8.0,
        'rarity': 'Эпический',
        'color': '🟣',  # Фиолетовый
        'sell_price': 1000,
        'require_premium': False,
        'variants': 10,
    },
    'legendary': {
        'name': '🟡 Легендарные',
        'emoji': '🐼',
        'cost': 10000,
        'income_per_hour_base': 20.0,
        'rarity': 'Легендарный',
        'color': '🟡',  # Жёлтый
        'sell_price': 5000,
        'require_premium': True,  # Только за донат
        'variants': 10,
    },
}

BEAR_NAMES = {
    'common': [
        'Мишка', 'Помидор', 'Никита', 'Маркус', 'Гриша',
        'Данте', 'Голиаф', 'Удалц', 'Нусси', 'Лола',
    ],
    'rare': [
        'Конрад', 'Макс', 'Павел', 'Антон', 'Патрик',
        'Виктор', 'Леонард', 'Костя', 'Денис', 'Тим',
    ],
    'epic': [
        'Копфы', 'Зефир', 'Мефистофель', 'Лорды', 'Нарниан',
        'Орфей', 'Тэкс', 'Ораль', 'Танатос', 'Посейдон',
    ],
    'legendary': [
        'Один', 'Тор', 'Локи', 'Окулт', 'Небуло',
        'Галилей', 'Невроз', 'Мевала', 'Ментор', 'Титан',
    ],
}

MAX_BEAR_LEVEL = 50  # Максимальный уровень


class BearsService:
    """Service for managing bears."""
    
    @staticmethod
    async def get_user_bears(session: AsyncSession, user_id: int) -> list[Bear]:
        """
        Get all bears for a user sorted by type and ID.
        """
        query = select(Bear).where(Bear.owner_id == user_id).order_by(Bear.bear_type, Bear.id)
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_bear_number(session: AsyncSession, bear_id: int, user_id: int) -> int:
        """
        Get the sequential number of a bear for this user.
        """
        bears = await BearsService.get_user_bears(session, user_id)
        for idx, bear in enumerate(bears, 1):
            if bear.id == bear_id:
                return idx
        return -1
    
    @staticmethod
    def get_bear_income_for_level(base_income: float, level: int) -> float:
        """
        Calculate income for a given level.
        Each level increases income by 20%.
        """
        return base_income * (1.2 ** (level - 1))
    
    @staticmethod
    async def create_bear(
        session: AsyncSession,
        user_id: int,
        bear_type: str,
        variant: int = None,
        name: str = None
    ) -> Bear:
        """
        Create a new bear for user.
        Variant: 1-10 для каждого класса.
        """
        if bear_type not in BEAR_CLASSES:
            raise ValueError(f"Invalid bear type: {bear_type}")
        
        bear_info = BEAR_CLASSES[bear_type]
        
        # Если вариант не указан, выбираем случайный
        if variant is None:
            variant = random.randint(1, bear_info['variants'])
        else:
            if not 1 <= variant <= bear_info['variants']:
                raise ValueError(f"Invalid variant: {variant}")
        
        bear_names = BEAR_NAMES[bear_type]
        bear_name = bear_names[variant - 1]  # Каждые 10 медведей разные
        
        income_per_hour = BearsService.get_bear_income_for_level(
            bear_info['income_per_hour_base'], 
            1  # Начинаем с 1 уровня
        )
        
        bear = Bear(
            owner_id=user_id,
            bear_type=bear_type,
            variant=variant,
            name=name or f"{bear_name} #{random.randint(1000, 9999)}",
            coins_per_hour=income_per_hour,
            coins_per_day=income_per_hour * 24,
        )
        session.add(bear)
        await session.commit()
        return bear
    
    @staticmethod
    async def upgrade_bear(session: AsyncSession, bear_id: int, user_id: int) -> Bear:
        """
        Upgrade a bear to the next level.
        Cost: 50 * current_level coins.
        Max level: 50
        """
        query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            raise ValueError("Медведь не найден")
        
        if bear.level >= MAX_BEAR_LEVEL:
            raise ValueError(f"Медведь уже на максимальном уровне ({MAX_BEAR_LEVEL})")
        
        upgrade_cost = 50 * bear.level
        user_query = select(User).where(User.id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        if user.coins < upgrade_cost:
            raise ValueError(f"Недостаточно коинов! Нужно {upgrade_cost}, у вас {user.coins:.0f}")
        
        # Upgrade bear
        bear_info = BEAR_CLASSES[bear.bear_type]
        bear.level += 1
        
        # Новые доходы для нового уровня
        new_income = BearsService.get_bear_income_for_level(
            bear_info['income_per_hour_base'],
            bear.level
        )
        bear.coins_per_hour = new_income
        bear.coins_per_day = new_income * 24
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
            raise ValueError("Медведь не найден")
        
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
        bear_class = BEAR_CLASSES.get(bear.bear_type, BEAR_CLASSES['common'])
        boost_info = ""
        
        if bear.boost_until and bear.boost_until > datetime.utcnow():
            time_left = bear.boost_until - datetime.utcnow()
            hours = time_left.total_seconds() // 3600
            minutes = (time_left.total_seconds() % 3600) // 60
            boost_info = f"\n🔥 Буст активен: {int(hours)}ч {int(minutes)}м (x{bear.boost_multiplier})"
        
        # Нужно коинов для следующего уровня
        upgrade_cost = 50 * bear.level
        next_level_info = ""
        if bear.level < MAX_BEAR_LEVEL:
            next_level_info = f"\n\n⬆️ Улучшить: {upgrade_cost} коинов"
        else:
            next_level_info = f"\n\n🌟 Максимальный уровень!"
        
        return (
            f"{bear_class['emoji']} **{bear.name}**\n"
            f"Класс: {bear_class['name']}\n"
            f"Уровень: {bear.level}/{MAX_BEAR_LEVEL}\n"
            f"Доход: {bear.coins_per_hour:.1f} коинов/час\n"
            f"Доход в день: {bear.coins_per_day:.1f} коинов\n"
            f"Можно обменять на: {bear_class['sell_price']} коинов\n"
            f"Куплен: {bear.purchased_at.strftime('%d.%m.%Y')}"
            f"{next_level_info}"
            f"{boost_info}"
        )
    
    @staticmethod
    async def format_bear_card(bear: Bear, bear_number: int) -> str:
        """
        Format bear card for display in list (brief info).
        """
        bear_class = BEAR_CLASSES.get(bear.bear_type, BEAR_CLASSES['common'])
        
        return (
            f"{bear_class['color']} **№{bear_number}** {bear_class['emoji']} {bear.name}\n"
            f"Уровень: {bear.level}/{MAX_BEAR_LEVEL} | "
            f"Доход: {bear.coins_per_hour:.1f}/ч | "
            f"Обмен: {bear_class['sell_price']}"
        )
    
    @staticmethod
    async def sell_bear(session: AsyncSession, bear_id: int, user_id: int) -> float:
        """
        Sell a bear and get its sell price.
        """
        query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            raise ValueError("Медведь не найден")
        
        bear_class = BEAR_CLASSES.get(bear.bear_type, BEAR_CLASSES['common'])
        refund = bear_class['sell_price']
        
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
            raise ValueError("Медведь не найден")
        
        if len(new_name) > 50:
            raise ValueError("Имя слишком длинное")
        
        bear.name = new_name
        await session.commit()
        return bear
    
    @staticmethod
    def get_bear_class_info(bear_type: str) -> dict:
        """
        Get bear class information.
        """
        return BEAR_CLASSES.get(bear_type, BEAR_CLASSES['common'])
