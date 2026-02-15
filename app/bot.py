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
        from app.handlers import (
            start, 
            bears, 
            shop, 
            profile, 
            admin, 
            cases, 
            exchange, 
            payment,
            daily_rewards,
            premium,
            nft,
            ads,
            bear_upgrades,
            pvp,
            tutorial,
            partnerships
        )
        
        # Register routers (order matters!)
        dp.include_router(start.router)  # Must be first for /start command
        dp.include_router(tutorial.router)
        dp.include_router(daily_rewards.router)
        dp.include_router(bears.router)
        dp.include_router(bear_upgrades.router)
        dp.include_router(shop.router)
        dp.include_router(cases.router)
        dp.include_router(profile.router)
        dp.include_router(exchange.router)
        dp.include_router(payment.router)
        dp.include_router(premium.router)
        dp.include_router(nft.router)
        dp.include_router(ads.router)
        dp.include_router(pvp.router)
        dp.include_router(partnerships.router)
        dp.include_router(admin.router)  # Admin must be last
        
        logger.info("✅ All handlers registered successfully")
    except Exception as e:
        logger.error(f"❌ Error setting up handlers: {e}", exc_info=True)
        raise


def setup_middlewares():
    """
    Setup middlewares (rate limiting, logging, etc.).
    """
    try:
        from app.middlewares.rate_limit import RateLimitMiddleware
        from app.middlewares.logging_middleware import LoggingMiddleware
        
        # Add rate limiting
        dp.message.middleware(RateLimitMiddleware())
        dp.callback_query.middleware(RateLimitMiddleware())
        
        # Add logging
        dp.message.middleware(LoggingMiddleware())
        dp.callback_query.middleware(LoggingMiddleware())
        
        logger.info("✅ Middlewares setup completed")
    except Exception as e:
        logger.warning(f"⚠️ Could not setup middlewares: {e}")


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
        
        # Setup middlewares
        logger.info("🔧 Setting up middlewares...")
        setup_middlewares()
        
        logger.info("🚀 Bot setup completed successfully!")
        
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
        
        # Close bot session
        await bot.session.close()
        logger.info("✅ Bot session closed")
    except Exception as e:
        logger.error(f"❌ Error closing bot: {e}", exc_info=True)
