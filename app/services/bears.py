"""Service for managing bears."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Bear, User
from datetime import datetime, timedelta
import random

# Bear classification system with 15 variants per rarity class
BEAR_CLASSES = {
    'common': {
        'name': '🐻 Обычные',
        'emoji': '🐻️',
        'rarity': 'Обычный',
        'color': '⚪',
        'require_premium': False,
        'variants': 15,
    },
    'rare': {
        'name': '🟢 Редкие',
        'emoji': '🐻',
        'rarity': 'Редкий',
        'color': '🟢',
        'require_premium': False,
        'variants': 15,
    },
    'epic': {
        'name': '🟣 Эпические',
        'emoji': '🐼',
        'rarity': 'Эпический',
        'color': '🟣',
        'require_premium': False,
        'variants': 15,
    },
    'legendary': {
        'name': '🟡 Легендарные',
        'emoji': '🐻‍❄️',
        'rarity': 'Легендарный',
        'color': '🟡',
        'require_premium': True,
        'variants': 15,
    },
}

BEAR_NAMES = {
    'common': [
        'Мишка', 'Помидор', 'Никита', 'Маркус', 'Гриша',
        'Данте', 'Голиаф', 'Удалец', 'Нусси', 'Лола',
        'Парти', 'Малис', 'Адам', 'Лев', 'Эмиль',
    ],
    'rare': [
        'Конрад', 'Макс', 'Павел', 'Антон', 'Патрик',
        'Виктор', 'Леонард', 'Костя', 'Денис', 'Тим',
        'Филипп', 'Эрнест', 'Грегори', 'Андрей', 'Мартин',
    ],
    'epic': [
        'Кофы', 'Зефир', 'Мефистофель', 'Лорды', 'Нарниан',
        'Орфей', 'Тэкс', 'Оральь', 'Танатос', 'Посейдон',
        'Аполлон', 'Артемида', 'Эрос', 'Церера', 'Морфей',
    ],
    'legendary': [
        'Один', 'Тор', 'Локи', 'Окулт', 'Небуло',
        'Галилей', 'Невроз', 'Мевала', 'Ментор', 'Титан',
        'Атлас', 'Прометей', 'Геракл', 'Эол', 'Арес',
    ],
}

MAX_BEAR_LEVEL = 50


class BearsService:
    """Service for managing bears."""
    
    @staticmethod
    def get_bear_stats(bear_type: str, variant: int) -> dict:
        """
        Get bear stats for a specific variant.
        Each variant is 5% more expensive and generates 5% more income.
        """
        base_stats = {
            'common': {'cost': 100, 'income': 1.0, 'sell': 50},
            'rare': {'cost': 500, 'income': 3.0, 'sell': 250},
            'epic': {'cost': 2000, 'income': 8.0, 'sell': 1000},
            'legendary': {'cost': 10000, 'income': 20.0, 'sell': 5000},
        }
        
        if bear_type not in base_stats:
            raise ValueError(f"Invalid bear type: {bear_type}")
        
        if not 1 <= variant <= 15:
            raise ValueError(f"Invalid variant: {variant}")
        
        base = base_stats[bear_type]
        # Каждый вариант на 5% дороже и доходнее
        multiplier = 1.05 ** (variant - 1)
        
        return {
            'cost': int(base['cost'] * multiplier),
            'income': base['income'] * multiplier,
            'sell': int(base['sell'] * multiplier),
        }
    
    @staticmethod
    def get_upgrade_cost(level: int) -> int:
        """
        Calculate upgrade cost for a bear.
        Exponential growth:
        Level 1->2: 50 coins
        Level 2->3: 150 coins (50 * 1.1^(2-1))
        Level 3->4: 340 coins (50 * 1.1^(3-1))
        etc.
        """
        # Базовая стоимость улучшения
        base_cost = 50
        # Коэффициент экспоненциального роста
        multiplier = 1.1 ** (level - 1)
        return int(base_cost * multiplier)
    
    @staticmethod
    def get_bear_income_for_level(base_income: float, level: int) -> float:
        """
        Calculate income for a given level.
        Diminishing returns:
        Level 1: base income
        Level 2: base income * 1.08
        Level 3: base income * 1.15
        Level 4: base income * 1.21
        etc.
        Growth slows as level increases.
        """
        # Меньший мультипликатор для дохода (8% за уровень вместо 20%)
        return base_income * (1.08 ** (level - 1))
    
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
    async def create_bear(
        session: AsyncSession,
        user_id: int,
        bear_type: str,
        variant: int = None,
        name: str = None
    ) -> Bear:
        """
        Create a new bear for user.
        Variant: 1-15 для каждого класса.
        """
        if bear_type not in BEAR_CLASSES:
            raise ValueError(f"Invalid bear type: {bear_type}")
        
        # Если вариант не указан, выбираем случайный
        if variant is None:
            variant = random.randint(1, 15)
        else:
            if not 1 <= variant <= 15:
                raise ValueError(f"Invalid variant: {variant}")
        
        bear_names = BEAR_NAMES[bear_type]
        bear_name = bear_names[variant - 1]
        
        stats = BearsService.get_bear_stats(bear_type, variant)
        income_per_hour = BearsService.get_bear_income_for_level(stats['income'], 1)
        
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
        Cost grows exponentially, income grows with diminishing returns.
        Max level: 50
        """
        query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user_id)
        result = await session.execute(query)
        bear = result.scalar_one_or_none()
        
        if not bear:
            raise ValueError("Медведь не найден")
        
        if bear.level >= MAX_BEAR_LEVEL:
            raise ValueError(f"Медведь уже на максимальном уровне ({MAX_BEAR_LEVEL})")
        
        upgrade_cost = BearsService.get_upgrade_cost(bear.level)
        user_query = select(User).where(User.id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        if user.coins < upgrade_cost:
            raise ValueError(f"Недостаточно коинов! Нужно {upgrade_cost}, у вас {user.coins:.0f}")
        
        # Upgrade bear
        bear.level += 1
        
        # Get base income for this variant
        stats = BearsService.get_bear_stats(bear.bear_type, bear.variant)
        new_income = BearsService.get_bear_income_for_level(stats['income'], bear.level)
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
        stats = BearsService.get_bear_stats(bear.bear_type, bear.variant)
        boost_info = ""
        
        if bear.boost_until and bear.boost_until > datetime.utcnow():
            time_left = bear.boost_until - datetime.utcnow()
            hours = time_left.total_seconds() // 3600
            minutes = (time_left.total_seconds() % 3600) // 60
            boost_info = f"\n🔥 Буст активен: {int(hours)}ч {int(minutes)}м (x{bear.boost_multiplier})"
        
        # Стоимость улучшения для следующего уровня
        next_upgrade_cost = BearsService.get_upgrade_cost(bear.level)
        next_level_income = BearsService.get_bear_income_for_level(stats['income'], bear.level + 1)
        income_increase = next_level_income - bear.coins_per_hour
        next_level_info = ""
        if bear.level < MAX_BEAR_LEVEL:
            next_level_info = (
                f"\n\n⬆️ Улучшить: {next_upgrade_cost} коинов\n"
                f"💰 Доход увеличится: +{income_increase:.2f} коин/ч"
            )
        else:
            next_level_info = f"\n\n🌟 Максимальный уровень!"
        
        return (
            f"{bear_class['emoji']} **{bear.name}**\n"
            f"Класс: {bear_class['name']}\n"
            f"Вариант: {bear.variant}/15\n"
            f"Уровень: {bear.level}/{MAX_BEAR_LEVEL}\n"
            f"💰 Основной доход: {stats['income']:.1f} коин/ч\n"
            f"💰 Текущий доход: {bear.coins_per_hour:.2f} коин/ч\n"
            f"📅 Доход в день: {bear.coins_per_day:.2f} коин\n"
            f"Можно обменять на: {stats['sell']} коинов\n"
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
        stats = BearsService.get_bear_stats(bear.bear_type, bear.variant)
        
        return (
            f"{bear_class['color']} **№{bear_number}** {bear_class['emoji']} {bear.name}\n"
            f"Вариант: {bear.variant}/15 | Уровень: {bear.level}/{MAX_BEAR_LEVEL} | "
            f"Доход: {bear.coins_per_hour:.2f}/ч | Обмен: {stats['sell']}"
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
        
        stats = BearsService.get_bear_stats(bear.bear_type, bear.variant)
        refund = stats['sell']
        
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
