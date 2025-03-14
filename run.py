"""
Main entry point for the Tourist Guide Bot.
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from typing import Dict, Any, Callable, Awaitable, Union

from app import logger
from app.handlers import router
from app.generators import init_http_client, close_http_client
from app.database import BotDatabase

# Database middleware
class DatabaseMiddleware:
    """Middleware for injecting database into handler data."""
    
    def __init__(self, db: BotDatabase):
        self.db = db
    
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        # Inject database into handler data
        data["db"] = self.db
        return await handler(event, data)

async def main():
    """Initialize and run the main bot."""
    try:
        # Import environment variables
        import os
        from dotenv import load_dotenv
        
        # Load environment variables (redundant but safe)
        load_dotenv()
        
        # Fetch required environment variables
        tg_token = os.getenv("TG_TOKEN")
        
        if not tg_token:
            logger.error("TG_TOKEN environment variable is not set")
            return
            
        # Initialize database
        db = BotDatabase()
        
        # Initialize HTTP client for all API requests
        await init_http_client()
        
        # Initialize bot and dispatcher with FSM storage
        bot = Bot(token=tg_token)
        dp = Dispatcher(storage=MemoryStorage())
        
        # Create and register database middleware
        db_middleware = DatabaseMiddleware(db)
        
        # Include router
        dp.include_router(router)
        
        # Register middleware at dispatcher level
        dp.message.middleware(db_middleware)
        dp.callback_query.middleware(db_middleware)  # Also apply to callback queries
        
        # Set bot commands
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Start interacting with the bot"),
            ]
        )
        
        # Log bot info
        me = await bot.get_me()
        logger.info(f"Starting bot as @{me.username} (ID: {me.id})")
        
        # Skip pending updates and start polling
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot is running...")
        
        try:
            await dp.start_polling(bot)
        finally:
            # Close the HTTP client properly when bot stops
            await close_http_client()
            
    except Exception as e:
        logger.error(f"Main bot error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)