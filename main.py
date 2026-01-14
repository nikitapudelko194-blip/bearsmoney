"""BearsMoney Bot - Main entry point."""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.bot import bot, dp, setup_bot, close_bot
    from config import settings
except Exception as e:
    print(f"❌ Error importing modules: {e}")
    print(f"Python path: {sys.path}")
    sys.exit(1)

# Configure logging
try:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.LOG_DIR / 'bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
except Exception as e:
    print(f"❌ Error setting up logging: {e}")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)


async def main():
    """
    Main function - start bot polling.
    """
    try:
        logger.info("="*60)
        logger.info("🐻 Starting BearsMoney Bot...")
        logger.info("="*60)
        
        # Проверка обязательных параметров
        if not settings.BOT_TOKEN:
            raise ValueError("❌ BOT_TOKEN не установлен в .env файле!")
        
        logger.info(f"✅ BOT_TOKEN: {settings.BOT_TOKEN[:20]}...")
        logger.info(f"✅ ADMIN_ID: {settings.ADMIN_ID}")
        logger.info(f"✅ DATABASE_URL: {settings.DATABASE_URL}")
        logger.info(f"✅ DEBUG: {settings.DEBUG}")
        
        # Setup bot
        logger.info("🔧 Setting up bot...")
        await setup_bot()
        logger.info("✅ Bot setup completed")
        
        logger.info("📡 Starting polling...")
        logger.info("🤖 Bot is running! Send /start to test")
        logger.info("Press Ctrl+C to stop")
        
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except ValueError as e:
        logger.error(f"⚠️  Configuration Error: {e}")
        print(f"\n❌ {e}\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        print(f"\n❌ ОШИБКА: {e}\n")
        sys.exit(1)
    finally:
        logger.info("🛑 Closing bot...")
        await close_bot()
        await bot.session.close()
        logger.info("✅ Bot closed")


if __name__ == "__main__":
    try:
        print("""
╔════════════════════════════════════════════════════════╗
║          🐻 БеарсМани - Telegram Bot                  ║
║                                                        ║
║  Запуск бота...                                        ║
║  Если видите ошибки - проверьте .env файл            ║
╚════════════════════════════════════════════════════════╝
        """)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Бот остановлен пользователем")
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}\n")
        logger.critical(f"Critical error: {e}", exc_info=True)
        sys.exit(1)
