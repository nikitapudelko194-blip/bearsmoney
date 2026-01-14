"""Bot initialization and dispatcher setup."""
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings

logger = logging.getLogger(__name__)

try:
    # Create bot and dispatcher
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    logger.info("✅ Bot and Dispatcher created successfully")
except Exception as e:
    logger.error(f"❌ Error creating bot: {e}")
    raise


def setup_handlers():
    """
    Setup all command handlers.
    """
    try:
        # Import handlers
        from app.handlers import start, bears, shop
        
        # Register routers
        dp.include_router(start.router)
        dp.include_router(bears.router)
        dp.include_router(shop.router)
        
        logger.info("✅ All handlers registered successfully")
    except Exception as e:
        logger.error(f"❌ Error setting up handlers: {e}", exc_info=True)
        raise


async def setup_bot():
    """
    Setup bot before polling starts.
    """
    try:
        logger.info("🔧 Initializing database...")
        # Initialize database
        from app.database.db import init_db
        await init_db()
        logger.info("✅ Database initialized")
        
        # Setup handlers
        logger.info("🔧 Setting up handlers...")
        setup_handlers()
        logger.info("✅ Handlers setup completed")
        
    except Exception as e:
        logger.error(f"❌ Error in setup_bot: {e}", exc_info=True)
        raise


async def close_bot():
    """
    Close bot gracefully.
    """
    try:
        logger.info("🔧 Closing database connection...")
        from app.database.db import close_db
        await close_db()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}", exc_info=True)
