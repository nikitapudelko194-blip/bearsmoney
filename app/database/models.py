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
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referred_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bears = relationship('Bear', back_populates='owner')
    coins_transactions = relationship('CoinTransaction', back_populates='user')
    withdrawals = relationship('Withdrawal', back_populates='user')
    subscriptions = relationship('Subscription', back_populates='user')
    completed_quests = relationship('Quest', secondary='user_quests', back_populates='completed_by')
    referrals = relationship('User', backref='referrer', remote_side=[referrer_id])


class Bear(Base):
    """Bear model."""
    __tablename__ = 'bears'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    bear_type = Column(String(50), nullable=False)  # 'common', 'rare', 'epic', 'legendary'
    name = Column(String(255))
    level = Column(Integer, default=1)
    coins_per_hour = Column(Float, default=1.0)
    coins_per_day = Column(Float, default=24.0)
    boost_multiplier = Column(Float, default=1.0)  # For boosts
    boost_until = Column(DateTime, nullable=True)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship('User', back_populates='bears')


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
