"""
Tourist Guide Bot Application Package.
This package contains all the core functionality for the tourist guide bot.
"""

import logging
import os
from dotenv import load_dotenv

# Set up logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("tourist_bot.log"),
    ]
)

# Create logger that will be used across the application
logger = logging.getLogger("tourist_bot")

# Load environment variables
load_dotenv()

# Validate critical environment variables
required_vars = [
    "TG_TOKEN", 
    "ADMIN_BOT_TOKEN",
    "DEEPSEEK_API_KEY",
    "YA_SPEECHKIT_API_KEY",
    "YA_SEARCH_API_KEY"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    
# Initialize shared HTTP client
http_client = None

# Database path
DB_PATH = os.getenv("DB_PATH", "bot_stats.db")

# Admin configuration
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "letmein")  # Default password, should be changed
AUTHORIZED_ADMIN_IDS = [
    113872890,  # Replace with your actual admin ID
]