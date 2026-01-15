"""Service for managing loot cases."""
import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User, UserCase, CaseReward, Bear, CoinTransaction
from app.services.bears import BearsService
from datetime import datetime

# Case types and their costs
CASE_TYPES = {
    'common': {
        'name': '📋 Обычный ящик',
        'emoji': '📋',
        'cost_coins': 200,
        'cost_ton': 0,
        'description': '💰 Коины (100-500) | 😭 Пустота | 💵 ТОН | 🐻 Медведи',
    },
    'rare': {
        'name': '📦 Редкий ящик',
        'emoji': '📦',
        'cost_coins': 1000,
        'cost_ton': 0,
        'description': '💰 Коины (500-3000) | 😭 Пустота | 💵 ТОН | 🐻 Редкие Медведи',
    },
    'epic': {
        'name': '🔥 Эпический ящик',
        'emoji': '🔥',
        'cost_coins': 0,
        'cost_ton': 1.0,
        'description': '💵 ТОН (0.1-1) | 💰 Коины (5K-10K) | 😭 Пустота | 🔥 Эпические Медведи',
    },
    'legendary': {
        'name': '🌟 Легендарный ящик',
        'emoji': '🌟',
        'cost_coins': 0,
        'cost_ton': 5.0,
        'description': '💵 ТОН (1-2) | 💰 Коины (10K-20K) | 😭 Пустота | 🌟 Легендарные Медведи',
    },
}

# Loot table for common cases (coins)
# COST: 200 coins - rewards UP TO 500 coins (UPDATED!)
COMMON_CASE_LOOT = [
    # (reward_type, reward_value, rarity, weight)
    # Coins are most common
    ('coins', 100, 'common', 400),
    ('coins', 200, 'common', 300),
    ('coins', 300, 'common', 200),
    ('coins', 500, 'common', 100),
    ('empty', 0, 'empty', 500),  # Empty is also very common
    # TON (very rare)
    ('ton', 0.1, 'legendary', 5),
    # Common bears
    ('bear', 'common:1', 'common', 20),
    ('bear', 'common:3', 'common', 15),
    ('bear', 'common:5', 'common', 10),
    # Rare bears (rare)
    ('bear', 'rare:1', 'rare', 5),
]

# Loot table for rare cases (coins)
# COST: 1000 coins - BALANCED (reduced big rewards)
RARE_CASE_LOOT = [
    # More coins
    ('coins', 500, 'common', 300),
    ('coins', 1000, 'common', 250),
    ('coins', 2000, 'rare', 80),      # REDUCED from 150 (10.3% → 5.8%)
    ('coins', 3000, 'rare', 40),      # REDUCED from 100 (6.8% → 2.9%)
    ('empty', 0, 'empty', 480),       # INCREASED from 400 (27.4% → 31.6%)
    # TON (very rare) - REDUCED
    ('ton', 0.1, 'legendary', 4),     # REDUCED from 8 (0.5% → 0.3%)
    ('ton', 0.5, 'legendary', 2),     # REDUCED from 3 (0.2% → 0.1%)
    # More bears
    ('bear', 'common:5', 'common', 40),
    ('bear', 'common:10', 'common', 30),
    ('bear', 'rare:3', 'rare', 25),
    ('bear', 'rare:5', 'rare', 15),
    ('bear', 'rare:8', 'rare', 10),
]

# Loot table for epic cases (TON) - BALANCED
# COST: 1 TON (~$5-10)
EPIC_CASE_LOOT = [
    # TON rewards - BALANCED
    ('ton', 0.1, 'common', 290),      # INCREASED from 250 (17.2% → 20.0%)
    ('ton', 0.5, 'common', 150),      # Same (10.3%)
    ('ton', 1.0, 'rare', 50),         # REDUCED from 80 (5.5% → 3.5%)
    ('empty', 0, 'empty', 415),       # INCREASED from 350 (24.1% → 28.6%)
    # COINS - BALANCED
    ('coins', 5000, 'rare', 150),     # Same (10.3%)
    ('coins', 10000, 'epic', 45),     # REDUCED from 80 (5.5% → 3.0%)
    # Epic bears
    ('bear', 'epic:1', 'epic', 80),
    ('bear', 'epic:3', 'epic', 70),
    ('bear', 'epic:5', 'epic', 60),
    ('bear', 'epic:8', 'epic', 50),
    # Legendary bears (rare)
    ('bear', 'legendary:1', 'legendary', 25),
    ('bear', 'legendary:3', 'legendary', 15),
]

# Loot table for legendary cases (TON) - REBALANCED (VARIANT 1)
# COST: 5 TON (~$25-50)
# FOCUS: More coins, less bears!
LEGENDARY_CASE_LOOT = [
    # TON rewards - UNCHANGED
    ('ton', 1.0, 'rare', 200),        # 11.0% (unchanged)
    ('ton', 2.0, 'epic', 73),         # 4.0% (unchanged)
    ('empty', 0, 'empty', 328),       # 18.0% (unchanged)
    # COINS - SIGNIFICANTLY INCREASED!
    ('coins', 10000, 'epic', 273),    # INCREASED from 91 (5.0% → 15.0%) ⬆️ +200%
    ('coins', 20000, 'epic', 182),    # INCREASED from 46 (2.5% → 10.0%) ⬆️ +300%
    # Legendary bears - REDUCED (all weights ~40% less)
    ('bear', 'legendary:1', 'legendary', 36),   # REDUCED from 60
    ('bear', 'legendary:2', 'legendary', 42),   # REDUCED from 70
    ('bear', 'legendary:3', 'legendary', 39),   # REDUCED from 65
    ('bear', 'legendary:4', 'legendary', 36),   # REDUCED from 60
    ('bear', 'legendary:5', 'legendary', 42),   # REDUCED from 70
    ('bear', 'legendary:6', 'legendary', 36),   # REDUCED from 60
    ('bear', 'legendary:7', 'legendary', 33),   # REDUCED from 55
    ('bear', 'legendary:8', 'legendary', 42),   # REDUCED from 70
    ('bear', 'legendary:9', 'legendary', 36),   # REDUCED from 60
    ('bear', 'legendary:10', 'legendary', 39),  # REDUCED from 65
    ('bear', 'legendary:11', 'legendary', 36),  # REDUCED from 60
    ('bear', 'legendary:12', 'legendary', 33),  # REDUCED from 55
    ('bear', 'legendary:13', 'legendary', 30),  # REDUCED from 50
    ('bear', 'legendary:14', 'legendary', 27),  # REDUCED from 45
    ('bear', 'legendary:15', 'legendary', 24),  # REDUCED from 40
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
        
        # ✅ CRITICAL FIX: Check if user has enough coins/TON
        if case_info['cost_coins'] > 0:
            if user.coins < case_info['cost_coins']:
                raise ValueError(f"❌ Недостаточно коинов!\nНужно: {case_info['cost_coins']:,.0f}\nУ вас: {user.coins:,.0f}")
            user.coins -= case_info['cost_coins']
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-case_info['cost_coins'],
                transaction_type='case_open',
                description=f'Открытие {case_info["name"]} (-{case_info["cost_coins"]:,.0f} коинов)'
            )
            session.add(transaction)
        
        # ✅ CRITICAL FIX: Check TON balance if case costs TON
        if case_info['cost_ton'] > 0:
            if user.ton_balance < case_info['cost_ton']:
                raise ValueError(
                    f"❌ Недостаточно TON!\n\n"
                    f"Нужно: {case_info['cost_ton']:.2f} TON\n"
                    f"У вас: {user.ton_balance:.4f} TON\n\n"
                    f"💡 Как получить TON:\n"
                    f"1. Зарабатывайте Coins с медведями\n"
                    f"2. Обменяйте Coins на TON в '💱 Обмен'"
                )
            
            # ✅ Deduct TON from balance
            user.ton_balance -= case_info['cost_ton']
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-case_info['cost_ton'],
                transaction_type='case_open_ton',
                description=f'Открытие {case_info["name"]} (-{case_info["cost_ton"]:.2f} TON)'
            )
            session.add(transaction)
        
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
            result['reward_message'] = f"💰 Коины: +{reward_value:,.0f}"
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=reward_value,
                transaction_type='case_reward',
                description=f'Награда из {case_info["name"]} (+{reward_value:,.0f} коинов)'
            )
            session.add(transaction)
            
        elif reward_type == 'ton':
            # ✅ Add TON to user balance
            user.ton_balance += reward_value
            result['reward_message'] = f"💵 ТОН: +{reward_value:.4f}"
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=reward_value,
                transaction_type='case_reward_ton',
                description=f'Награда из {case_info["name"]} (+{reward_value:.4f} TON)'
            )
            session.add(transaction)
            
        elif reward_type == 'bear':
            # Parse bear info (e.g., 'rare:5' or 'legendary:10')
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
            cost_text = f"💰 {case_info['cost_coins']:,} коинов"
        if case_info['cost_ton'] > 0:
            if cost_text:
                cost_text += f" или "
            cost_text += f"💵 {case_info['cost_ton']:.1f} ТОН"
        
        return (
            f"{case_info['emoji']} **{case_info['name']}**\n"
            f"Цена: {cost_text}\n"
            f"💴 Призы: {case_info['description']}"
        )
    
    @staticmethod
    def format_case_result(result: dict) -> str:
        """
        Format case opening result for display.
        """
        rarity_emoji = {
            'empty': '⭕',
            'common': '🟢',
            'rare': '🟪',
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
