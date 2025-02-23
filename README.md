# Street Spirit

## Description
Street Spirit is a Telegram bot designed to provide guided tours. Users can share their location or specify an address, and the bot will provide information about nearby tourist attractions, including historical information, websites, images, and even audio descriptions.

## Features
- Responds to the `/start` command with a welcome message.
- Handles location messages to find nearby tourist attractions.
- Provides detailed information about the nearest tourist attraction, including:
  - Name and address
  - Historical information generated using Yandex GPT
  - Relevant websites and images
  - Audio description generated using Yandex SpeechKit

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/street-spirit.git
    cd street-spirit
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Create a [.env](http://_vscodecontentref_/1) file in the root directory and add the required environment variables:
    ```env
    TG_TOKEN=your_telegram_bot_token
    YA_TOKEN=your_yandex_api_token
    YA_MODELURI=your_yandex_model_uri
    YA_SPEECHKIT_API_KEY=your_yandex_speechkit_api_key
    HERE_API_KEY=your_here_maps_api_key
    YA_SEARCH_API_KEY=your_yandex_search_api_key
    YA_CATALOG_ID=your_yandex_catalog_id
    ```

## Usage

1. Run the bot:
    ```sh
    python run.py
    ```

2. Open Telegram and start a chat with your bot. Use the `/start` command to begin interacting with the bot.

3. Share your location or send an address to receive information about nearby tourist attractions.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.