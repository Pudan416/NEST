"""
Script to run both the Tourist Guide Bot and Admin Bot simultaneously.
Optimized for cloud deployment platforms like Railway.
"""

import asyncio
import sys
import os
import signal
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("run_all")


async def run_main_bot():
    """Run the main tourist guide bot."""
    try:
        from run import main as main_bot_main
        logger.info("Starting main tourist guide bot...")
        await main_bot_main()
    except Exception as e:
        logger.error(f"Main bot error: {e}", exc_info=True)


async def run_admin_bot():
    """Run the admin bot."""
    try:
        from admin_bot import main as admin_bot_main
        logger.info("Starting admin bot...")
        await admin_bot_main()
    except Exception as e:
        logger.error(f"Admin bot error: {e}", exc_info=True)


async def main():
    """Run both bots concurrently."""
    logger.info("Starting both bots...")
    
    # Check for required environment variables (минимальный набор для запуска)
    required_vars = ["TG_TOKEN", "ADMIN_BOT_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing critical environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in Railway Dashboard or your environment")
        sys.exit(1)
    
    # Проверяем дополнительные переменные (предупреждения, не критичные ошибки)
    optional_vars = ["GOOGLE_MAPS_API_KEY", "DEEPSEEK_API_KEY", "YA_SPEECHKIT_API_KEY", "YA_SEARCH_API_KEY"]
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    if missing_optional:
        logger.warning(f"Missing optional environment variables: {', '.join(missing_optional)}")
        logger.warning("Some features may not work properly without these variables")
    
    # Показываем какие переменные установлены
    logger.info("Environment variables status:")
    all_vars = required_vars + optional_vars + ["ADMIN_PASSWORD", "DB_PATH"]
    for var in all_vars:
        value = os.getenv(var)
        if value:
            # Маскируем значения для безопасности
            masked_value = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
            logger.info(f"  {var}: {masked_value}")
        else:
            logger.info(f"  {var}: NOT SET")
    
    try:
        # Run both bots concurrently
        await asyncio.gather(
            run_main_bot(),
            run_admin_bot(),
            return_exceptions=True
        )
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal. Stopping bots...")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bots stopped manually.")
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)