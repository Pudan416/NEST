# Tourist Guide Bot

A Telegram bot that helps users discover interesting places nearby. The bot includes a separate admin interface for monitoring usage statistics.

## Features

### Main Bot
- Discover nearby tourist attractions, landmarks, and points of interest
- Get detailed information about places including:
  - Historical descriptions
  - Audio narration
  - Distance information
  - Address details
  - Walking directions
  - Place photos
- Automatic translation of place names and descriptions
- Support for various tourist attraction types:
  - Museums and Art Galleries
  - Religious Sites (Churches, Temples, Mosques, Synagogues)
  - Parks and Nature Areas
  - Tourist Attractions and Landmarks
  - Cultural Sites
- Customizable place preferences
- Multi-language support (English and Russian)

### Admin Bot
- Monitor bot usage statistics
- View active users
- See which cities the bot has been used in
- Create database backups
- Test API connections
- Debug system information

## Project Structure

```
/street_spirit
├── app/
│   ├── handlers/
│   │   ├── __init__.py      # Router and shared data
│   │   ├── state.py         # Shared state and constants
│   │   ├── common.py        # Common utilities
│   │   ├── start.py         # Start and language commands
│   │   ├── places.py        # Place preferences handling
│   │   └── location.py      # Location and place discovery
│   ├── __init__.py          # App initialization
│   ├── google_maps.py       # Google Maps API integration
│   ├── languages.py         # Language management
│   └── database.py          # Database operations
├── run.py                   # Main bot entry point
├── admin_bot.py             # Admin bot entry point
├── run_all.py              # Run both bots together
├── requirements.txt         # Project dependencies
├── setup.py                # Package configuration
└── .env                    # Environment variables (not in repo)
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd street_spirit
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

4. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root with your API keys:
   ```
   # Telegram Tokens
   TG_TOKEN=your_main_bot_token
   ADMIN_BOT_TOKEN=your_admin_bot_token

   # API Keys
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   YA_SPEECHKIT_API_KEY=your_yandex_speechkit_key

   # Admin Access
   ADMIN_PASSWORD=your_secure_password

   # Database
   DB_PATH=bot_stats.db
   ```

6. Add your Telegram user ID to `app/__init__.py` in the `AUTHORIZED_ADMIN_IDS` list for automatic admin access.

## Running the Bots

### Running Both Bots Together
```bash
python run_all.py
```

### Running Bots Separately

Start the main Tourist Guide Bot:
```bash
python run.py
```

Start the Admin Bot:
```bash
python admin_bot.py
```

## Usage

### Main Bot

1. Start a chat with your bot on Telegram
2. Send the `/start` command and select your preferred language
3. Use `/places` to customize your place preferences (optional)
4. Share your location to find nearby attractions
5. For each place you'll get:
   - A brief description
   - Historical information
   - Photos (if available)
   - Walking directions
   - Google Maps link
6. Use the navigation buttons to:
   - Get more details about the place
   - See it on Google Maps
   - Move to the next place
   - Return to the first place

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

- **Google Maps Places API**: For finding nearby places and place details
- **Google Maps Directions API**: For walking directions
- **Google Maps Geocoding API**: For address lookup
- **DeepSeek API**: For generating historical descriptions
- **Yandex SpeechKit**: For text-to-speech conversion

## Performance Optimization

The bot includes several optimizations:
1. Concurrent API requests using `asyncio.gather()`
2. Request deduplication for API calls
3. Rate limiting for expensive operations
4. Efficient place data caching
5. Modular code structure for better maintainability

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Add your preferred license information here]

## Credits

Konstantin Pudan [pudan.me]
