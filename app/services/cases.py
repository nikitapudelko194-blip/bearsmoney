"""Service for managing loot cases."""
import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User, UserCase, CaseReward, Bear
from app.services.bears import BearsService
from datetime import datetime

# Case types and their costs
CASE_TYPES = {
    'common': {
        'name': '📋 Обычный ящик',
        'emoji': '📋',
        'cost_coins': 1000,
        'cost_ton': 0,
        'description': 'Низкие шансы на медведей',
    },
    'rare': {
        'name': '📦 Редкий ящик',
        'emoji': '📦',
        'cost_coins': 5000,
        'cost_ton': 0,
        'description': 'Лучшие шансы, всё щё',
    },
    'epic': {
        'name': '🔥 Эпический ящик',
        'emoji': '🔥',
        'cost_coins': 0,
        'cost_ton': 1.0,
        'description': 'ТОН: Эпические и легендарные медведи',
    },
    'legendary': {
        'name': '🌟 Легендарный ящик',
        'emoji': '🌟',
        'cost_coins': 0,
        'cost_ton': 5.0,
        'description': 'ТОН: Очень большие награды',
    },
}

# Loot table for common cases (coins)
COMMON_CASE_LOOT = [
    # (reward_type, reward_value, rarity, weight)
    # Coins are most common
    ('coins', 500, 'common', 400),
    ('coins', 1000, 'common', 300),
    ('coins', 2000, 'common', 200),
    ('empty', 0, 'empty', 500),  # Empty is also very common
    # Rare coins
    ('coins', 5000, 'rare', 50),
    # Common bears
    ('bear', 'common:1', 'common', 30),
    ('bear', 'common:3', 'common', 25),
    ('bear', 'common:5', 'common', 15),
    # Rare bears (rare)
    ('bear', 'rare:1', 'rare', 10),
    ('bear', 'rare:2', 'rare', 8),
]

# Loot table for rare cases (coins)
RARE_CASE_LOOT = [
    # More coins
    ('coins', 2000, 'common', 300),
    ('coins', 5000, 'common', 250),
    ('coins', 10000, 'rare', 150),
    ('coins', 20000, 'rare', 100),
    ('empty', 0, 'empty', 400),  # Still common
    # More bears
    ('bear', 'common:5', 'common', 50),
    ('bear', 'common:10', 'common', 40),
    ('bear', 'rare:3', 'rare', 35),
    ('bear', 'rare:5', 'rare', 25),
    ('bear', 'rare:8', 'rare', 15),
]

# Loot table for epic cases (TON)
EPIC_CASE_LOOT = [
    # TON rewards
    ('ton', 2.0, 'common', 250),
    ('ton', 5.0, 'rare', 150),
    ('ton', 10.0, 'rare', 100),
    ('empty', 0, 'empty', 300),  # Still very common
    # Epic bears
    ('bear', 'epic:1', 'epic', 80),
    ('bear', 'epic:3', 'epic', 70),
    ('bear', 'epic:5', 'epic', 60),
    ('bear', 'epic:8', 'epic', 50),
    # Legendary bears (rare)
    ('bear', 'legendary:1', 'legendary', 25),
    ('bear', 'legendary:3', 'legendary', 15),
]

# Loot table for legendary cases (TON)
LEGENDARY_CASE_LOOT = [
    # Large TON rewards
    ('ton', 10.0, 'rare', 200),
    ('ton', 20.0, 'epic', 120),
    ('ton', 50.0, 'epic', 80),
    ('empty', 0, 'empty', 200),  # Still common
    # Many legendary bears
    ('bear', 'legendary:2', 'legendary', 100),
    ('bear', 'legendary:5', 'legendary', 90),
    ('bear', 'legendary:8', 'legendary', 80),
    ('bear', 'legendary:10', 'legendary', 70),
    ('bear', 'legendary:12', 'legendary', 50),
    ('bear', 'legendary:15', 'legendary', 30),
]

LOOT_TABLES = {
    'common': COMMON_CASE_LOOT,
    'rare': RARE_CASE_LOOT,
    'epic': EPIC_CASE_LOOT,
    'legendary': LEGENDARY_CASE_LOOT,
}


class CasesService:
    """Service for managing loot cases."""
    
    @staticmethod
    def get_case_info(case_type: str) -> dict:
        """
        Get case information.
        """
        return CASE_TYPES.get(case_type, CASE_TYPES['common'])
    
    @staticmethod
    def _roll_reward(case_type: str) -> tuple:
        """
        Roll a random reward from the loot table.
        Returns (reward_type, reward_value, rarity)
        """
        loot_table = LOOT_TABLES.get(case_type, COMMON_CASE_LOOT)
        
        # Calculate total weight
        total_weight = sum(item[3] for item in loot_table)
        
        # Roll
        roll = random.randint(1, total_weight)
        current = 0
        
        for reward_type, reward_value, rarity, weight in loot_table:
            current += weight
            if roll <= current:
                return (reward_type, reward_value, rarity)
        
        # Fallback (should not happen)
        return ('empty', 0, 'empty')
    
    @staticmethod
    async def open_case(session: AsyncSession, user_id: int, case_type: str) -> dict:
        """
        Open a case and give reward to user.
        Returns dict with result information.
        """
        if case_type not in CASE_TYPES:
            raise ValueError(f"Неизвестный тип ящика: {case_type}")
        
        # Get user
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Пользователь не найден")
        
        case_info = CASE_TYPES[case_type]
        
        # Check if user has enough coins/TON
        if case_info['cost_coins'] > 0:
            if user.coins < case_info['cost_coins']:
                raise ValueError(f"Недостаточно коинов! Нужно {case_info['cost_coins']}, у вас {user.coins:.0f}")
            user.coins -= case_info['cost_coins']
        
        # TODO: Check TON balance if needed (need integration with wallet)
        
        # Roll reward
        reward_type, reward_value, rarity = CasesService._roll_reward(case_type)
        
        result = {
            'case_type': case_type,
            'reward_type': reward_type,
            'reward_value': reward_value,
            'rarity': rarity,
            'bear_created': None,
        }
        
        # Apply reward
        if reward_type == 'coins':
            user.coins += reward_value
            result['reward_message'] = f"💰 Коины: +{reward_value:.0f}"
        elif reward_type == 'ton':
            # TODO: Add TON to user wallet
            result['reward_message'] = f"💵 ТОН: +{reward_value:.2f}"
        elif reward_type == 'bear':
            # Parse bear info (e.g., 'rare:5')
            bear_type, variant = reward_value.split(':')
            variant = int(variant)
            bear = await BearsService.create_bear(session, user.id, bear_type, variant=variant)
            result['bear_created'] = bear
            bear_class = BearsService.get_bear_class_info(bear_type)
            result['reward_message'] = f"{bear_class['emoji']} Медведь: {bear.name} (Вариант {variant}/15)"
        elif reward_type == 'empty':
            result['reward_message'] = "😭 Пусто..."
        
        await session.commit()
        return result
    
    @staticmethod
    def format_case_info(case_type: str) -> str:
        """
        Format case information for display.
        """
        case_info = CASE_TYPES.get(case_type, CASE_TYPES['common'])
        
        cost_text = ""
        if case_info['cost_coins'] > 0:
            cost_text = f"💰 {case_info['cost_coins']} коинов"
        if case_info['cost_ton'] > 0:
            if cost_text:
                cost_text += f" или "
            cost_text += f"💵 {case_info['cost_ton']:.1f} ТОН"
        
        return (
            f"{case_info['emoji']} **{case_info['name']}**\n"
            f"Цена: {cost_text}\n"
            f"Описание: {case_info['description']}"
        )
    
    @staticmethod
    def format_case_result(result: dict) -> str:
        """
        Format case opening result for display.
        """
        rarity_emoji = {
            'empty': '⭕',
            'common': '🟢',
            'rare': '🟣',
            'epic': '🔥',
            'legendary': '🌟',
        }
        
        emoji = rarity_emoji.get(result['rarity'], '⭕')
        case_type = result['case_type']
        case_info = CASE_TYPES[case_type]
        
        text = (
            f"{case_info['emoji']} **Открытые ящики!**\n\n"
            f"{emoji} **{result['reward_message']}**"
        )
        
        return text
