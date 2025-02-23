import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from app.handlers import router

# Load environment variables
load_dotenv()

async def main():
    # Fetch required environment variables
    tg_token = os.getenv('TG_TOKEN')
    ya_token = os.getenv('YA_TOKEN')
    ya_modeluri = os.getenv('YA_MODELURI')

    if not all([tg_token, ya_token, ya_modeluri]):
        raise ValueError("Required environment variables (TG_TOKEN, YA_TOKEN, YA_MODELURI) are not set.")

    # Initialize bot and dispatcher
    bot = Bot(token=tg_token)
    dp = Dispatcher()
    dp.include_router(router)

    # Set bot commands
    await bot.set_my_commands([BotCommand(command="start", description="Start interacting with the bot")])

    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")
    except Exception as e:
        print(f"An error occurred: {e}")