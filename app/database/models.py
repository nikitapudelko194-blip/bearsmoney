"""SQLAlchemy models for the database."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class User(Base):
    """User model."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    coins = Column(Float, default=0)
    level = Column(Integer, default=1)
    experience = Column(Float, default=0)
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime, nullable=True)
    wallet_address = Column(String(255), nullable=True)
    
    # Реферальная система
    referred_by = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Кто пригласил
    referred_count = Column(Integer, default=0)  # Сколько людей пригласил
    referral_earnings_level1 = Column(Float, default=0)  # Заработок с 1 круга
    referral_earnings_level2 = Column(Float, default=0)  # Заработок со 2 круга
    referral_earnings_level3 = Column(Float, default=0)  # Заработок с 3 круга
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bears = relationship('Bear', back_populates='owner', foreign_keys='Bear.owner_id')
    coins_transactions = relationship('CoinTransaction', back_populates='user')
    withdrawals = relationship('Withdrawal', back_populates='user')
    subscriptions = relationship('Subscription', back_populates='user')
    completed_quests = relationship('Quest', secondary='user_quests', back_populates='completed_by')
    achievements = relationship('UserAchievement', back_populates='user')
    daily_logins = relationship('UserDailyLogin', back_populates='user')
    case_history = relationship('CaseHistory', back_populates='user')
    bear_insurance = relationship('BearInsurance', back_populates='user')
    # Fixed: Specify foreign_keys explicitly to avoid ambiguity
    p2p_listings_as_seller = relationship('P2PListing', back_populates='seller', foreign_keys='P2PListing.seller_id')
    p2p_listings_as_buyer = relationship('P2PListing', back_populates='buyer', foreign_keys='P2PListing.buyer_id')
    
    # Реферальная система: связь с реферером и рефералами
    referrer = relationship('User', remote_side=[id], foreign_keys=[referred_by], backref='referrals')


class Bear(Base):
    """Bear model."""
    __tablename__ = 'bears'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    bear_type = Column(String(50), nullable=False)  # 'common', 'rare', 'epic', 'legendary'
    variant = Column(Integer, default=1)  # 1-15 для каждого класса
    name = Column(String(255))
    level = Column(Integer, default=1)
    coins_per_hour = Column(Float, default=1.0)
    coins_per_day = Column(Float, default=24.0)
    boost_multiplier = Column(Float, default=1.0)  # For boosts
    boost_until = Column(DateTime, nullable=True)
    total_coins_earned = Column(Float, default=0)  # Статистика дохода
    is_locked = Column(Boolean, default=False)  # Лок от продажи
    is_on_sale = Column(Boolean, default=False)  # На ли медведь на продаже (P2P)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship('User', back_populates='bears', foreign_keys=[owner_id])
    insurance = relationship('BearInsurance', back_populates='bear', uselist=False)
    p2p_listings = relationship('P2PListing', back_populates='bear')


class CoinTransaction(Base):
    """Coin transaction model."""
    __tablename__ = 'coin_transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # 'earn', 'spend', 'quest_reward', 'referral'
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='coins_transactions')


class Withdrawal(Base):
    """Withdrawal model for crypto payouts."""
    __tablename__ = 'withdrawals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    amount_coins = Column(Float, nullable=False)
    amount_crypto = Column(Float, nullable=False)
    crypto_type = Column(String(20), default='TON')  # 'TON', 'BTC', 'ETH', 'USDT'
    wallet_address = Column(String(255), nullable=False)
    status = Column(String(20), default='pending')  # 'pending', 'processing', 'completed', 'failed'
    tx_hash = Column(String(255), nullable=True)
    commission = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship('User', back_populates='withdrawals')


class Subscription(Base):
    """Premium subscription model."""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    tier = Column(String(50), default='basic')  # 'basic', 'premium', 'vip'
    coins_bonus = Column(Float, default=0.1)  # Bonus multiplier: 10% extra income
    commission_reduction = Column(Float, default=0.01)  # Reduction: 1% commission reduction
    withdraw_limit = Column(Float, default=1000)
    status = Column(String(20), default='active')
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='subscriptions')


class Quest(Base):
    """Quest model."""
    __tablename__ = 'quests'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    quest_type = Column(String(50), nullable=False)  # 'buy_bear', 'collect_coins', 'invite_friends', 'daily'
    target_value = Column(Float, default=1)  # How many bears to buy, coins to collect, etc.
    reward_coins = Column(Float, default=100)
    reward_ton = Column(Float, default=0)
    duration_days = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    completed_by = relationship(
        'User', 
        secondary='user_quests',
        back_populates='completed_quests'
    )


class UserQuest(Base):
    """User quest completion tracking."""
    __tablename__ = 'user_quests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    quest_id = Column(Integer, ForeignKey('quests.id'), nullable=False, index=True)
    progress = Column(Float, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)


class CaseReward(Base):
    """Case reward model for loot boxes."""
    __tablename__ = 'case_rewards'
    
    id = Column(Integer, primary_key=True)
    case_type = Column(String(50), nullable=False)  # 'common', 'rare', 'epic'
    reward_type = Column(String(50), nullable=False)  # 'coins', 'ton', 'bear'
    reward_value = Column(Float, nullable=False)
    rarity = Column(String(20), nullable=False)  # 'common', 'rare', 'epic', 'legendary'
    drop_chance = Column(Float, default=0.1)  # 10%
    created_at = Column(DateTime, default=datetime.utcnow)


class UserCase(Base):
    """User case opening tracking."""
    __tablename__ = 'user_cases'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    case_type = Column(String(50), nullable=False)
    reward_id = Column(Integer, ForeignKey('case_rewards.id'), nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow)


class ChannelTask(Base):
    """Channel subscription task model."""
    __tablename__ = 'channel_tasks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    reward_claimed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ========== НОВЫЕ МОДЕЛИ ДЛЯ НОВЫХ ФУНКЦИЙ ==========

class UserAchievement(Base):
    """Достижения пользователя."""
    __tablename__ = 'user_achievements'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    achievement_type = Column(String(100), nullable=False)  # 'first_million', 'collector', 'max_level', 'legendary_bear', 'billionaire'
    achievement_name = Column(String(255), nullable=False)
    achievement_description = Column(Text)
    reward_coins = Column(Float, default=0)
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    is_hidden = Column(Boolean, default=False)  # Скрытые достижения (спойлер)
    
    # Relationships
    user = relationship('User', back_populates='achievements')


class UserDailyLogin(Base):
    """Ежедневные логины - ежедневные награды."""
    __tablename__ = 'user_daily_logins'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    streak_days = Column(Integer, default=1)  # Текущая полоса дней подряд
    last_login_date = Column(DateTime, nullable=True)  # Последний логин
    total_logins = Column(Integer, default=1)  # Всего логинов
    reward_claimed_today = Column(Boolean, default=False)  # Получена ли награда сегодня
    last_reward_claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='daily_logins')


class CaseHistory(Base):
    """История открытия кейсов с RTP статистикой."""
    __tablename__ = 'case_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    case_type = Column(String(50), nullable=False)  # 'common', 'rare', 'epic', 'legendary'
    reward_type = Column(String(50), nullable=False)  # 'coins', 'ton', 'bear', 'empty'
    reward_value = Column(Float, nullable=False)  # Сколько получено
    case_cost = Column(Float, nullable=False)  # Сколько потратил
    bear_id = Column(Integer, ForeignKey('bears.id'), nullable=True)  # Если получил медведя
    opened_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='case_history')


class BearInsurance(Base):
    """Страховка для редких медведей - защита от потери."""
    __tablename__ = 'bear_insurance'
    
    id = Column(Integer, primary_key=True)
    bear_id = Column(Integer, ForeignKey('bears.id'), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    is_active = Column(Boolean, default=True)  # Активна ли страховка
    insurance_type = Column(String(50), default='24h')  # '24h', '48h', 'permanent'
    cost_coins = Column(Float, default=5000)  # Стоимость страховки в коинах
    activated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Когда истекает (если не вечна)
    
    # Relationships
    bear = relationship('Bear', back_populates='insurance')
    user = relationship('User', back_populates='bear_insurance')


class P2PListing(Base):
    """P2P торговля медведями между игроками."""
    __tablename__ = 'p2p_listings'
    
    id = Column(Integer, primary_key=True)
    bear_id = Column(Integer, ForeignKey('bears.id'), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # None = выставлено на продажу
    price_coins = Column(Float, nullable=False)  # Цена в коинах
    status = Column(String(20), default='active')  # 'active', 'sold', 'cancelled'
    created_at = Column(DateTime, default=datetime.utcnow)
    sold_at = Column(DateTime, nullable=True)
    
    # Relationships
    bear = relationship('Bear', back_populates='p2p_listings')
    seller = relationship('User', back_populates='p2p_listings_as_seller', foreign_keys=[seller_id])
    buyer = relationship('User', back_populates='p2p_listings_as_buyer', foreign_keys=[buyer_id])


class CaseGuarantee(Base):
    """Гарантии в кейсах - каждый N-й кейс гарантированно редкий/эпический."""
    __tablename__ = 'case_guarantees'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    case_type = Column(String(50), nullable=False)  # 'common', 'rare', 'epic', 'legendary'
    opened_count = Column(Integer, default=0)  # Сколько открыто кейсов
    
    # Гарантии:
    # common кейсы: каждый 15-й гарантирует редкий
    # rare кейсы: каждый 50-й гарантирует эпический
    # epic кейсы: каждый 100-й гарантирует легендарный
    
    guarantee_15 = Column(Integer, default=0)  # Счётчик до 15 (для common)
    guarantee_50 = Column(Integer, default=0)  # Счётчик до 50 (для rare)
    guarantee_100 = Column(Integer, default=0)  # Счётчик до 100 (для epic/legendary)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CaseTheme(Base):
    """Тематические кейсы - сезонные события."""
    __tablename__ = 'case_themes'
    
    id = Column(Integer, primary_key=True)
    theme_name = Column(String(100), nullable=False)  # 'black_friday', 'seasonal_winter', 'legendary'
    theme_emoji = Column(String(10))
    description = Column(Text)
    cost_coins = Column(Float, nullable=False)
    cost_ton = Column(Float, default=0)
    bonus_percent = Column(Float, default=0)  # % бонуса к наградам (Чёрная пятница +50%)
    is_active = Column(Boolean, default=True)
    is_seasonal = Column(Boolean, default=False)  # Сезонный ли кейс
    season = Column(String(50), nullable=True)  # 'winter', 'summer', 'spring', 'autumn'
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BearFusion(Base):
    """Переплавка медведей - 10 обычных = 1 редкий."""
    __tablename__ = 'bear_fusions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    input_bears = Column(String(500))  # JSON array ID медведей для переплавки
    input_count = Column(Integer, nullable=False)  # Количество (10, 50, 500 и т.д.)
    input_type = Column(String(50), nullable=False)  # 'common', 'rare', 'epic'
    output_type = Column(String(50), nullable=False)  # Какой тип получим ('rare', 'epic', 'legendary')
    output_bear_id = Column(Integer, ForeignKey('bears.id'), nullable=True)  # ID полученного медведя
    status = Column(String(20), default='pending')  # 'pending', 'completed', 'failed'
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
