"""Service for new game features."""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import (
    User, Bear, UserAchievement, UserDailyLogin, CaseHistory, 
    BearInsurance, P2PListing, CaseGuarantee, CaseTheme, BearFusion
)
from app.services.bears import BearsService

logger = logging.getLogger(__name__)

# Достижения
ACHIEVEMENTS = {
    'first_million': {
        'name': '🎦 Первый миллион',
        'description': 'Заработать 1,000,000 коинов',
        'reward': 10000,
    },
    'collector': {
        'name': '🃛 Коллекционер',
        'description': 'Обычные, редкие, эпические и легендарные медведи',
        'reward': 50000,
    },
    'max_level': {
        'name': '⭐ Максимальный уровень',
        'description': 'Прокачать медведя до 50 уровня',
        'reward': 100000,
    },
    'legendary_bear': {
        'name': '🐻‍❄️ Легендарный',
        'description': 'Получить легендарного медведя',
        'reward': 50000,
    },
    'billionaire': {
        'name': '🪨 Миллиардер',
        'description': 'Заработать 1,000,000,000 коинов',
        'reward': 500000,
    },
}

# Ежедневные награды
DAILY_REWARDS = {
    1: {'coins': 100, 'emoji': '💰'},
    2: {'coins': 200, 'emoji': '💰'},
    3: {'coins': 500, 'emoji': '💰'},
    4: {'coins': 750, 'emoji': '💰'},
    5: {'coins': 1000, 'emoji': '💰'},
    6: {'coins': 1500, 'emoji': '💰'},
    7: {'coins': 2500, 'emoji': '💰'},
    8: {'coins': 3500, 'emoji': '💰'},
    9: {'coins': 5000, 'emoji': '💰'},
    10: {'coins': 0, 'bear': 'common', 'emoji': '🐻'},  # 10-й день = обычный медведь
    11: {'coins': 6000, 'emoji': '💰'},
    15: {'coins': 0, 'bear': 'rare', 'emoji': '🐻'},  # 15-й день = редкий
    20: {'coins': 0, 'bear': 'rare', 'emoji': '🐻'},
    30: {'coins': 0, 'bear': 'epic', 'emoji': '🐼'},  # 30-й день = эпический
}


class FeaturesService:
    """Service for new game features."""
    
    # ============ ДОСТИЖЕНИЯ ============
    
    @staticmethod
    async def check_and_unlock_achievements(session: AsyncSession, user_id: int) -> list[dict]:
        """Проверить и разблокировать достижения."""
        unlocked = []
        user = await session.get(User, user_id)
        
        # Проверяем на дубликаты
        existing = await session.execute(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        )
        unlocked_types = {a.achievement_type for a in existing.scalars()}
        
        # "Первый миллион"
        if 'first_million' not in unlocked_types and user.experience >= 1000000:
            achievement = UserAchievement(
                user_id=user_id,
                achievement_type='first_million',
                achievement_name=ACHIEVEMENTS['first_million']['name'],
                achievement_description=ACHIEVEMENTS['first_million']['description'],
                reward_coins=ACHIEVEMENTS['first_million']['reward'],
            )
            session.add(achievement)
            user.coins += achievement.reward_coins
            unlocked.append(achievement)
        
        # "Коллекционер"
        if 'collector' not in unlocked_types:
            bears = await session.execute(select(Bear).where(Bear.owner_id == user_id))
            all_bears = bears.scalars().all()
            has_all_types = all(any(b.bear_type == t for b in all_bears) for t in ['common', 'rare', 'epic', 'legendary'])
            if has_all_types:
                achievement = UserAchievement(
                    user_id=user_id,
                    achievement_type='collector',
                    achievement_name=ACHIEVEMENTS['collector']['name'],
                    achievement_description=ACHIEVEMENTS['collector']['description'],
                    reward_coins=ACHIEVEMENTS['collector']['reward'],
                )
                session.add(achievement)
                user.coins += achievement.reward_coins
                unlocked.append(achievement)
        
        # "Максимальный уровень"
        if 'max_level' not in unlocked_types:
            bears = await session.execute(select(Bear).where(Bear.owner_id == user_id))
            if any(b.level >= 50 for b in bears.scalars()):
                achievement = UserAchievement(
                    user_id=user_id,
                    achievement_type='max_level',
                    achievement_name=ACHIEVEMENTS['max_level']['name'],
                    achievement_description=ACHIEVEMENTS['max_level']['description'],
                    reward_coins=ACHIEVEMENTS['max_level']['reward'],
                )
                session.add(achievement)
                user.coins += achievement.reward_coins
                unlocked.append(achievement)
        
        # "Легендарный"
        if 'legendary_bear' not in unlocked_types:
            bears = await session.execute(select(Bear).where(Bear.owner_id == user_id, Bear.bear_type == 'legendary'))
            if bears.scalar():
                achievement = UserAchievement(
                    user_id=user_id,
                    achievement_type='legendary_bear',
                    achievement_name=ACHIEVEMENTS['legendary_bear']['name'],
                    achievement_description=ACHIEVEMENTS['legendary_bear']['description'],
                    reward_coins=ACHIEVEMENTS['legendary_bear']['reward'],
                )
                session.add(achievement)
                user.coins += achievement.reward_coins
                unlocked.append(achievement)
        
        await session.commit()
        return unlocked
    
    # ============ ЕЖЕДНЕВНЫЕ ЛОГИНЫ ============
    
    @staticmethod
    async def get_or_create_daily_login(session: AsyncSession, user_id: int) -> UserDailyLogin:
        """Получить или создать запись ежедневных логинов."""
        login = await session.execute(
            select(UserDailyLogin).where(UserDailyLogin.user_id == user_id)
        )
        user_login = login.scalar()
        
        if not user_login:
            user_login = UserDailyLogin(user_id=user_id)
            session.add(user_login)
            await session.commit()
        
        return user_login
    
    @staticmethod
    async def claim_daily_reward(session: AsyncSession, user_id: int) -> dict:
        """Получить ежедневную награду."""
        user_login = await FeaturesService.get_or_create_daily_login(session, user_id)
        user = await session.get(User, user_id)
        
        today = datetime.utcnow().date()
        last_login = user_login.last_login_date.date() if user_login.last_login_date else None
        
        if user_login.reward_claimed_today and last_login == today:
            raise ValueError("Награда уже получена сегодня!")
        
        # Проверяются полосы (streak)
        if last_login and (datetime.utcnow().date() - last_login).days > 1:
            user_login.streak_days = 1  # Полоса ресетилась
        else:
            user_login.streak_days += 1
        
        # Получают награду
        reward = DAILY_REWARDS.get(user_login.streak_days, {'coins': 10000, 'emoji': '💰'})
        
        result = {
            'streak_day': user_login.streak_days,
            'reward_type': 'bear' if 'bear' in reward else 'coins',
            'reward_value': reward.get('coins', 0),
            'bear_type': reward.get('bear'),
            'emoji': reward.get('emoji'),
        }
        
        if reward.get('coins'):
            user.coins += reward['coins']
        
        if reward.get('bear'):
            bear = await BearsService.create_bear(session, user_id, reward['bear'])
            result['bear_created'] = bear
        
        user_login.reward_claimed_today = True
        user_login.last_login_date = datetime.utcnow()
        user_login.total_logins += 1
        user_login.last_reward_claimed_at = datetime.utcnow()
        
        await session.commit()
        return result
    
    # ============ ИСТОРИЯ КЕЙСОВ & RTP ============
    
    @staticmethod
    async def record_case_opening(session: AsyncSession, user_id: int, case_type: str, 
                                 reward_type: str, reward_value: float, case_cost: float, bear_id: int = None):
        """Записать открытие кейса в историю."""
        history = CaseHistory(
            user_id=user_id,
            case_type=case_type,
            reward_type=reward_type,
            reward_value=reward_value,
            case_cost=case_cost,
            bear_id=bear_id,
        )
        session.add(history)
        await session.commit()
    
    @staticmethod
    async def get_case_statistics(session: AsyncSession, user_id: int) -> dict:
        """Получить статистику кейсов и RTP."""
        history = await session.execute(
            select(CaseHistory).where(CaseHistory.user_id == user_id).order_by(desc(CaseHistory.opened_at))
        )
        all_openings = history.scalars().all()
        
        if not all_openings:
            return {'error': 'Нет открытых кейсов'}
        
        total_spent = sum(h.case_cost for h in all_openings)
        total_earned = sum(h.reward_value for h in all_openings if h.reward_type == 'coins') + \
                      sum(h.reward_value for h in all_openings if h.reward_type == 'ton') * 100000  # Приблизительно
        
        rtp = (total_earned / total_spent * 100) if total_spent > 0 else 0
        
        return {
            'total_opened': len(all_openings),
            'total_spent': total_spent,
            'total_earned': total_earned,
            'rtp_percent': round(rtp, 2),
            'profit': total_earned - total_spent,
            'last_10_openings': [{
                'type': h.case_type,
                'reward': h.reward_type,
                'value': h.reward_value,
                'time': h.opened_at
            } for h in all_openings[:10]]
        }
    
    # ============ СТРАХОВКА МЕДВЕДЕЙ ============
    
    @staticmethod
    async def insure_bear(session: AsyncSession, bear_id: int, user_id: int, hours: int = 24) -> BearInsurance:
        """Накупить страховку для медведя."""
        bear = await session.get(Bear, bear_id)
        if not bear or bear.owner_id != user_id:
            raise ValueError("Медведь не найден")
        
        user = await session.get(User, user_id)
        cost = 5000 if hours == 24 else 10000 if hours == 48 else 50000
        
        if user.coins < cost:
            raise ValueError(f"Недостаточно коинов! Нужно {cost}")
        
        insurance = BearInsurance(
            bear_id=bear_id,
            user_id=user_id,
            insurance_type=f"{hours}h",
            cost_coins=cost,
            expires_at=datetime.utcnow() + timedelta(hours=hours),
        )
        session.add(insurance)
        user.coins -= cost
        
        await session.commit()
        return insurance
    
    # ============ P2P ТОРГОВЛЯ ============
    
    @staticmethod
    async def list_bear_for_sale(session: AsyncSession, bear_id: int, user_id: int, price_coins: float) -> P2PListing:
        """Выставить медведя на продажу."""
        bear = await session.get(Bear, bear_id)
        if not bear or bear.owner_id != user_id:
            raise ValueError("Медведь не найден")
        
        listing = P2PListing(
            bear_id=bear_id,
            seller_id=user_id,
            price_coins=price_coins,
        )
        session.add(listing)
        await session.commit()
        return listing
    
    @staticmethod
    async def buy_bear_from_player(session: AsyncSession, listing_id: int, buyer_id: int) -> dict:
        """Купить медведя у другого игрока."""
        listing = await session.get(P2PListing, listing_id)
        if not listing or listing.status != 'active':
            raise ValueError("Лот не найден или уже куплен")
        
        buyer = await session.get(User, buyer_id)
        if buyer.coins < listing.price_coins:
            raise ValueError("Недостаточно коинов")
        
        seller = await session.get(User, listing.seller_id)
        bear = await session.get(Bear, listing.bear_id)
        
        # Перевод средств
        buyer.coins -= listing.price_coins
        seller.coins += listing.price_coins
        
        # Перевод медведя
        bear.owner_id = buyer_id
        
        # Обновление лота
        listing.status = 'sold'
        listing.buyer_id = buyer_id
        listing.sold_at = datetime.utcnow()
        
        await session.commit()
        return {'success': True, 'message': 'Медведь куплен!'}
    
    # ============ ПЕРЕПЛАВКА МЕДВЕДеЙ ============
    
    @staticmethod
    async def fuse_bears(session: AsyncSession, user_id: int, bear_ids: list[int], input_type: str) -> dict:
        """Переплавить медведей (10 джентс = 1 редкий)"""
        # Определяем выходный тип
        if input_type == 'common':
            if len(bear_ids) != 10:
                raise ValueError("Нужно 10 обычных медведей")
            output_type = 'rare'
        elif input_type == 'rare':
            if len(bear_ids) != 10:
                raise ValueError("Нужно 10 редких медведей")
            output_type = 'epic'
        elif input_type == 'epic':
            if len(bear_ids) != 10:
                raise ValueError("Нужно 10 эпических медведей")
            output_type = 'legendary'
        else:
            raise ValueError("Неверный тип")
        
        # Проверяют эвеэство медведей
        bears = await session.execute(
            select(Bear).where(Bear.id.in_(bear_ids), Bear.owner_id == user_id, Bear.bear_type == input_type)
        )
        found_bears = bears.scalars().all()
        
        if len(found_bears) != len(bear_ids):
            raise ValueError("Невсе медведи найдены или имеют правильные типы")
        
        # Удаляем старых медведей
        for bear in found_bears:
            await session.delete(bear)
        
        # Создают нового
        new_bear = await BearsService.create_bear(session, user_id, output_type)
        
        # Минт fusion события
        fusion = BearFusion(
            user_id=user_id,
            input_bears=str(bear_ids),
            input_count=len(bear_ids),
            input_type=input_type,
            output_type=output_type,
            output_bear_id=new_bear.id,
            status='completed',
            completed_at=datetime.utcnow(),
        )
        session.add(fusion)
        await session.commit()
        
        return {'new_bear': new_bear, 'message': f'🐻 {input_type} x{len(bear_ids)} = {output_type}!'}
