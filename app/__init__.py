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

# Validate critical environment variables (необходимые для запуска)
critical_vars = [
    "TG_TOKEN", 
    "ADMIN_BOT_TOKEN"
]

missing_critical = [var for var in critical_vars if not os.getenv(var)]
if missing_critical:
    logger.error(f"Missing critical environment variables: {', '.join(missing_critical)}")
    logger.error("Bot cannot start without these variables!")
    
# Validate optional environment variables (для полной функциональности)
optional_vars = [
    "DEEPSEEK_API_KEY",
    "YA_SPEECHKIT_API_KEY", 
    "YA_SEARCH_API_KEY",
    "GOOGLE_MAPS_API_KEY"
]

missing_optional = [var for var in optional_vars if not os.getenv(var)]
if missing_optional:
    logger.warning(f"Missing optional environment variables: {', '.join(missing_optional)}")
    logger.warning("Some features may not work without these variables")
    
# Initialize shared HTTP client
http_client = None

# Database path
DB_PATH = os.getenv("DB_PATH", "bot_stats.db")

# Admin configuration
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "letmein")  # Default password, should be changed
AUTHORIZED_ADMIN_IDS = [
    113872890,  # Replace with your actual admin ID
]