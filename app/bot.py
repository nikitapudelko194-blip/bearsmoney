"""Bot initialization and dispatcher setup."""
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings

logger = logging.getLogger(__name__)

# Create bot and dispatcher
bot = Bot(token=settings.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def setup_handlers():
    """
    Setup all command handlers.
    """
    # Import handlers
    from app.handlers import start
    
    # Register routers
    dp.include_router(start.router)
    
    logger.info("All handlers registered successfully")


async def setup_bot():
    """
    Setup bot before polling starts.
    """
    # Initialize database
    from app.database.db import init_db
    await init_db()
    
    # Setup handlers
    setup_handlers()
    
    logger.info("Bot setup completed")


async def close_bot():
    """
    Close bot gracefully.
    """
    from app.database.db import close_db
    await close_db()
    logger.info("Bot closed")
