"""BearsMoney Bot - Main entry point."""
import asyncio
import logging
from app.bot import bot, dp, setup_bot, close_bot
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_DIR / 'bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """
    Main function - start bot polling.
    """
    try:
        logger.info("Starting BearsMoney Bot...")
        
        # Setup bot
        await setup_bot()
        
        logger.info("Bot is polling...")
        # Start polling
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await close_bot()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
