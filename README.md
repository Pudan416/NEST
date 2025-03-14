# Tourist Guide Bot

A Telegram bot that helps users discover interesting places nearby. The bot includes a separate admin interface for monitoring usage statistics.

## Features

### Main Bot
- Discover nearby tourist attractions, landmarks, and points of interest
- Get detailed information about places including:
  - Historical descriptions
  - Audio narration
  - Images
  - Distance information
  - Address details
- Automatic translation of place names and descriptions to English
- Support for various tourist attraction types (museums, monuments, parks, etc.)

### Admin Bot
- Monitor bot usage statistics
- View active users
- See which cities the bot has been used in
- Create database backups
- Test API connections
- Debug system information

## Project Structure

```
/tourist_guide_bot
  /app
    __init__.py               # Initialize app package
    database.py               # Shared database functionality
    generators.py             # API integrations & data generation
    handlers.py               # Main bot message handlers
  run.py                      # Main bot entry point
  admin_bot.py                # Admin bot entry point
  run_all.py                  # Script to run both bots together
  requirements.txt            # Project dependencies
  .env                        # Shared environment variables (not in repo)
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd tourist_guide_bot
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your API keys:
   ```
   # Telegram Tokens
   TG_TOKEN=your_main_bot_token
   ADMIN_BOT_TOKEN=your_admin_bot_token

   # API Keys
   DEEPSEEK_API_KEY=your_deepseek_api_key
   YA_SPEECHKIT_API_KEY=your_yandex_speechkit_key
   YA_SEARCH_API_KEY=your_yandex_search_key
   YA_CATALOG_ID=your_yandex_catalog_id

   # Admin Access
   ADMIN_PASSWORD=your_secure_password

   # Database
   DB_PATH=bot_stats.db
   ```

4. Add your Telegram user ID to `app/__init__.py` in the `AUTHORIZED_ADMIN_IDS` list for automatic admin access.

## Running the Bots

### Running Both Bots Together

```
python run_all.py
```

### Running Bots Separately

Start the main Tourist Guide Bot:
```
python run.py
```

Start the Admin Bot:
```
python admin_bot.py
```

## Usage

### Main Bot

1. Start a chat with your bot on Telegram
2. Send the `/start` command
3. Share your location to find nearby attractions
4. Receive information about the closest attraction
5. Continue sharing different locations to discover more places

### Admin Bot

1. Start a chat with your admin bot on Telegram
2. Send the `/start` command
3. If your Telegram user ID is in the authorized list, you'll get immediate access
4. Otherwise, enter the admin password from your `.env` file
5. Use these commands to manage the bot:
   - `/stats` - View basic usage statistics
   - `/users` - View recent active users
   - `/cities` - View cities where the bot has searched
   - `/backup` - Create a database backup
   - `/test_api` - Test API connections
   - `/debug` - Show technical debugging information
   - `/help` - Show available commands

## APIs Used

- **DeepSeek API**: For generating historical descriptions and translations
- **Yandex SpeechKit**: For text-to-speech conversion
- **Yandex Search**: For finding images of attractions
- **Overpass API**: For finding nearby points of interest
- **Nominatim API**: For reverse geocoding (getting addresses from coordinates)

## Performance Optimization

If you experience slow response times from the DeepSeek API, you can try:

1. Reducing the `max_tokens` value in `generators.py` to get faster responses (at the cost of less detailed descriptions)
2. Implementing caching for frequently requested locations
3. Using parallel processing with `asyncio.gather()` to fetch data concurrently

## License

[Add your preferred license information here]

## Credits

[Add credits and acknowledgements here]