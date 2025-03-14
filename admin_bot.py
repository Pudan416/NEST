"""
Admin Bot for Tourist Guide Bot statistics and management.
"""

import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
import io

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app import logger, ADMIN_PASSWORD, AUTHORIZED_ADMIN_IDS, DB_PATH
from app.database import BotDatabase

# States for authentication FSM
class AuthStates(StatesGroup):
    waiting_for_password = State()

router = Router()

# Ensure database exists
db = BotDatabase(db_path=DB_PATH)

# Authorized users check
def is_authorized(user_id):
    """Check if a user is authorized by ID."""
    return user_id in AUTHORIZED_ADMIN_IDS

# Start command - entry point for the bot
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle the /start command."""
    user_id = message.from_user.id
    logger.info(f"Admin bot: Start command received from user {user_id}")
    
    if is_authorized(user_id):
        await message.answer(
            f"👋 Welcome to the Admin Panel Bot!\n\n"
            f"You are authorized as an admin. Use these commands to manage your bot:\n\n"
            f"/stats - View basic statistics\n"
            f"/users - View recent users\n"
            f"/cities - View cities where the bot has searched\n"
            f"/backup - Create database backup\n"
            f"/help - See all available commands"
        )
    else:
        await message.answer(
            "🔒 Welcome to the Admin Panel Bot!\n\n"
            "This bot provides admin access to the tourist guide bot statistics.\n\n"
            "Please enter the password to continue."
        )
        await state.set_state(AuthStates.waiting_for_password)

# Handle password submission
@router.message(AuthStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    """Process password authentication."""
    logger.info(f"Admin bot: Password attempt from user {message.from_user.id}")
    if message.text == ADMIN_PASSWORD:
        await state.clear()
        await message.answer(
            "✅ Password correct! You now have admin access.\n\n"
            "Available commands:\n"
            "/stats - View basic statistics\n"
            "/users - View recent users\n"
            "/cities - View cities where the bot has searched\n"
            "/backup - Create database backup\n"
            "/help - See all available commands"
        )
    else:
        await message.answer("❌ Incorrect password. Please try again or contact the bot owner.")

# Display basic stats
@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    """Display basic bot statistics."""
    user_id = message.from_user.id
    logger.info(f"Admin bot: Stats command from user {user_id}")
    
    # Check if the user is in an auth state
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer("Please complete authentication first.")
        return
    
    # Check if user is authorized
    if not is_authorized(user_id) and current_state is None:
        await message.answer("You are not authorized to use this command.")
        return
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        await message.answer("Database not found. Please run the main bot first to create it.")
        return
    
    try:
        # Get statistics from database
        total_users = db.get_user_count()
        total_searches = db.get_search_count()
        active_users_today = db.get_active_users_today()
        
        # Get current time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        stats_message = (
            "📊 <b>Bot Statistics</b>\n\n"
            f"👥 <b>Total Users:</b> {total_users}\n"
            f"🔍 <b>Total Searches:</b> {total_searches}\n"
            f"👤 <b>Active Users Today:</b> {active_users_today}\n\n"
            f"Generated at: {current_time}"
        )
        
        await message.answer(stats_message, parse_mode="HTML")
    except Exception as e:
        error_msg = f"Error retrieving stats: {str(e)}"
        logger.error(error_msg)
        await message.answer(f"Error: {error_msg}")

# Display recent users
@router.message(Command("users"))
async def cmd_users(message: Message, state: FSMContext):
    """Display recent active users."""
    user_id = message.from_user.id
    logger.info(f"Admin bot: Users command from user {user_id}")
    
    # Check authorization
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer("Please complete authentication first.")
        return
    
    if not is_authorized(user_id) and current_state is None:
        await message.answer("You are not authorized to use this command.")
        return
    
    try:
        recent_users = db.get_recent_users(limit=10)
        
        if not recent_users:
            await message.answer("No users found in the database.")
            return
        
        users_message = "👥 <b>Recent Active Users</b>\n\n"
        
        for i, user in enumerate(recent_users, 1):
            username = user.get("username") or "No username"
            first_name = user.get("first_name") or "Unknown"
            last_name = user.get("last_name") or ""
            last_active = user.get("last_active") or "Unknown"
            
            users_message += (
                f"{i}. <b>User:</b> {first_name} {last_name} (@{username})\n"
                f"   <b>ID:</b> {user.get('user_id')}\n"
                f"   <b>Last active:</b> {last_active}\n\n"
            )
        
        await message.answer(users_message, parse_mode="HTML")
    except Exception as e:
        error_msg = f"Error retrieving users: {str(e)}"
        logger.error(error_msg)
        await message.answer(f"Error: {error_msg}")

## Popular places command removed as requested

# Create database backup
@router.message(Command("backup"))
async def cmd_backup(message: Message, state: FSMContext):
    """Create a backup of the database."""
    user_id = message.from_user.id
    logger.info(f"Admin bot: Backup command from user {user_id}")
    
    # Check authorization
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer("Please complete authentication first.")
        return
    
    if not is_authorized(user_id) and current_state is None:
        await message.answer("You are not authorized to use this command.")
        return
    
    try:
        backup_path = db.backup_database()
        
        if backup_path:
            await message.answer(f"✅ Database backup created successfully: {backup_path}")
        else:
            await message.answer("❌ Failed to create database backup.")
    except Exception as e:
        error_msg = f"Error creating backup: {str(e)}"
        logger.error(error_msg)
        await message.answer(f"Error: {error_msg}")

# Help command
@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    """Display help information."""
    user_id = message.from_user.id
    logger.info(f"Admin bot: Help command from user {user_id}")
    
    # Check authorization
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer("Please complete authentication first.")
        return
    
    if not is_authorized(user_id) and current_state is None:
        await message.answer("You are not authorized to use this command.")
        return
    
    help_message = (
        "📚 <b>Admin Bot Help</b>\n\n"
        "Available commands:\n\n"
        "/stats - View basic statistics (total users, searches, etc.)\n"
        "/users - View list of recent active users\n"
        "/popular - View most popular searched places\n"
        "/backup - Create a database backup\n"
        "/debug - Show technical debugging information\n"
        "/help - Show this help message"
    )
    
    await message.answer(help_message, parse_mode="HTML")

# Add cities command
@router.message(Command("cities"))
async def cmd_cities(message: Message, state: FSMContext):
    """Display cities where searches have been performed."""
    user_id = message.from_user.id
    logger.info(f"Admin bot: Cities command from user {user_id}")
    
    # Check authorization
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer("Please complete authentication first.")
        return
    
    if not is_authorized(user_id) and current_state is None:
        await message.answer("You are not authorized to use this command.")
        return
    
    try:
        cities = db.get_cities(limit=20)
        
        if not cities:
            await message.answer("No city data found in the database.")
            return
        
        cities_message = "🌆 <b>Cities Where the Bot Has Searched</b>\n\n"
        
        for i, (city, count) in enumerate(cities, 1):
            cities_message += (
                f"{i}. <b>{city or 'Unknown'}</b>: {count} searches\n"
            )
        
        await message.answer(cities_message, parse_mode="HTML")
    except Exception as e:
        error_msg = f"Error retrieving cities: {str(e)}"
        logger.error(error_msg)
        await message.answer(f"Error: {error_msg}")

# Add test_api command to admin bot
@router.message(Command("test_api"))
async def cmd_test_api(message: Message, state: FSMContext):
    """Test API connections."""
    user_id = message.from_user.id
    logger.info(f"Admin bot: Test API command from user {user_id}")
    
    # Check authorization
    current_state = await state.get_state()
    if current_state is not None:
        await message.answer("Please complete authentication first.")
        return
    
    if not is_authorized(user_id) and current_state is None:
        await message.answer("You are not authorized to use this command.")
        return
    
    try:
        from app.generators import test_deepseek_connection
        
        await message.answer("Testing DeepSeek API connection...")
        result = await test_deepseek_connection()
        await message.answer(f"DeepSeek API test result: {result}")
    except Exception as e:
        logger.error(f"Error in API test handler: {e}", exc_info=True)
        await message.answer(f"Error testing API: {str(e)}")

# Handle debug command
@router.message(Command("debug"))
async def cmd_debug(message: Message):
    """Display debug information."""
    user_id = message.from_user.id
    logger.info(f"Admin bot: Debug command from user {user_id}")
    
    # Debug info is available without authentication
    debug_info = (
        "🔍 <b>Debug Information</b>\n\n"
        f"Python version: {sys.version}\n"
        f"Bot is running: Yes\n"
        f"Database path: {DB_PATH}\n"
        f"Database exists: {os.path.exists(DB_PATH)}\n"
        f"Current directory: {os.getcwd()}\n"
        f"Authorized IDs: {AUTHORIZED_ADMIN_IDS}\n"
        f"User ID: {user_id}\n"
        f"Is admin: {is_authorized(user_id)}"
    )
    
    await message.answer(debug_info, parse_mode="HTML")

async def main():
    """Initialize and run the admin bot."""
    logger.info("Starting admin bot...")
    
    try:
        # Load token from environment variable
        admin_bot_token = os.getenv("ADMIN_BOT_TOKEN")
        
        if not admin_bot_token:
            logger.error("ADMIN_BOT_TOKEN environment variable is not set")
            return
        
        # Initialize Bot instance
        bot = Bot(token=admin_bot_token)
        
        # Initialize dispatcher with FSM storage
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
        
        # Print startup message
        me = await bot.get_me()
        logger.info(f"Admin bot started as @{me.username} (ID: {me.id})")
        
        # Skip pending updates and start polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Admin bot error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Admin bot stopped manually.")
    except Exception as e:
        logger.error(f"Critical error: {str(e)}", exc_info=True)
        sys.exit(1)