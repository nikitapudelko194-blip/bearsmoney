"""Configuration module for BearsMoney bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

class Settings:
    """Application settings."""
    
    # Telegram Bot
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    ADMIN_ID: int = int(os.getenv('ADMIN_ID', '0'))
    
    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql+asyncpg://user:password@localhost:5432/bearsmoney')
    DATABASE_POOL_SIZE: int = int(os.getenv('DATABASE_POOL_SIZE', '20'))
    
    # Redis
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Crypto Integration
    TON_API_URL: str = os.getenv('TON_API_URL', 'https://testnet.tonapi.io')
    TON_WALLET_ADDRESS: str = os.getenv('TON_WALLET_ADDRESS', '')
    TON_API_KEY: str = os.getenv('TON_API_KEY', '')
    
    # Payment
    STRIPE_API_KEY: str = os.getenv('STRIPE_API_KEY', '')
    PAYMENT_SYSTEM: str = os.getenv('PAYMENT_SYSTEM', 'stripe')
    
    # App Settings
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Game Economy
    MIN_WITHDRAW: float = float(os.getenv('MIN_WITHDRAW', '1.0'))  # Минимальный вывод 1 TON
    MAX_WITHDRAW: float = float(os.getenv('MAX_WITHDRAW', '100'))
    WITHDRAW_COMMISSION: float = float(os.getenv('WITHDRAW_COMMISSION', '0.02'))  # Комиссия 2% (0.02)
    COIN_TO_TON_RATE: float = float(os.getenv('COIN_TO_TON_RATE', '0.000002'))  # 1 TON = 500,000 Coins (0.5 TON = 250,000 Coins)
    
    # Channel Task
    CHANNEL_ID: str = os.getenv('CHANNEL_ID', '')
    CHANNEL_TASK_REWARD: float = float(os.getenv('CHANNEL_TASK_REWARD', '0.05'))
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent
    APP_DIR: Path = BASE_DIR / 'app'
    LOG_DIR: Path = BASE_DIR / 'logs'
    
    def __init__(self):
        self.LOG_DIR.mkdir(exist_ok=True)
        
        # Проверка обязательных параметров
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле!")
        if self.ADMIN_ID == 0:
            print("[⚠️  WARNING] ADMIN_ID установлен как 0. Функции администратора недоступны.")

settings = Settings()
