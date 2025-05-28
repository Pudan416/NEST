"""
Generator functions for the Tourist Guide Bot.
"""

import os
import asyncio
import httpx
from app import logger
from app.languages import get_api_prompt, get_api_message
import re

# Global HTTP client for reuse
_http_client = None


async def init_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


async def close_http_client():
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = await init_http_client()
    return _http_client


def _get_api_key(key_name):
    api_key = os.getenv(key_name)
    if not api_key:
        logger.error(f"{key_name} is not set in environment variables")
    return api_key


async def deepseek_request(
    payload, max_retries=3, http_client: httpx.AsyncClient = None
):
    url = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_API_KEY = _get_api_key("DEEPSEEK_API_KEY")

    if not DEEPSEEK_API_KEY:
        return get_api_message("deepseek_api_key_error")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    # Use the provided client if available, otherwise get the global one
    client_to_use = http_client if http_client else await get_http_client()

    # If http_client was passed, we assume it's managed externally (e.g., by the calling handler)
    # and we should not close it here.
    # The global client from get_http_client() is managed by init_http_client/close_http_client.

    for attempt in range(max_retries):
        try:
            logger.debug(
                f"Sending request to DeepSeek API (attempt {attempt+1}/{max_retries})"
            )

            response = await client_to_use.post(
                url, headers=headers, json=payload
            )  # Use client_to_use
            logger.debug(f"DeepSeek API response status: {response.status_code}")

            if response.status_code == 401:
                logger.error("Authentication error: Invalid API key")
                return get_api_message("invalid_api_key")

            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    retry_after = int(response.headers.get("retry-after", 1))
                    logger.warning(
                        f"Rate limited. Retrying after {retry_after} seconds"
                    )
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    return get_api_message("rate_limit_exceeded")

            elif response.status_code == 200:
                response_data = response.json()

                if "choices" in response_data and response_data["choices"]:
                    message = response_data["choices"][0].get("message", {})
                    content = message.get("content", "")
                    if content:
                        return content
                    else:
                        logger.error("No content found in DeepSeek response")
                        return get_api_message("no_content")
                else:
                    logger.error(f"Unexpected response format: {response_data}")
                    return get_api_message("unexpected_format")
            else:
                error_msg = f"API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                return f"Error: {error_msg}"

        except httpx.ConnectTimeout:
            logger.error(
                f"Connection timeout to DeepSeek API (attempt {attempt+1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff
                continue
            return get_api_message("connection_timeout")

        except httpx.ReadTimeout:
            logger.error(
                f"Read timeout from DeepSeek API (attempt {attempt+1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            return get_api_message("read_timeout")

        except Exception as e:
            error_msg = f"Exception in DeepSeek API request: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            return f"Error: {error_msg}"

    return get_api_message("multiple_failures")


async def test_deepseek_connection():
    simple_payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": get_api_prompt("deepseek_test_prompt")}
        ],
        "max_tokens": 10,
    }
    result = await deepseek_request(simple_payload)
    logger.info(f"DeepSeek connection test result: {result}")
    return result


async def translate_to_english(text: str):
    if (
        not text
        or text.strip() == ""
        or text == get_api_message("address_not_specified")
        or text == get_api_message("address_not_available")
    ):
        return text

    payload = {
        "model": "deepseek-chat",
        "temperature": 0.3,
        "max_tokens": 500,
        "messages": [
            {
                "role": "system",
                "content": get_api_prompt("translator_system_prompt"),
            },
            {
                "role": "user",
                "content": get_api_prompt("translate_prompt").format(text=text),
            },
        ],
    }

    result = await deepseek_request(payload)
    if result.startswith("Error:"):
        logger.error(f"Translation error: {result}")
        return text  # Return original text if translation fails

    return result


async def deepseek_location_info(
    city: str,
    street: str,
    poi_name: str,
    poi_address: str,
    original_name: str = None,
    http_client=None,
    lang: str = "en",
) -> str:
    """Generate location information using DeepSeek API."""
    try:
        if not http_client:
            http_client = await get_http_client()

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.error(get_api_message("deepseek_api_key_error"))
            return None

        # Add context about original name if available
        context = (
            f"Note: The original name of this place is '{original_name}'."
            if original_name
            else ""
        )

        # Use language-specific system prompt
        system_prompt = get_api_prompt(f"location_system_prompt_{lang}").format(
            city=city,
            poi_name=poi_name,
            poi_address=poi_address,
            context=context,
        )

        user_prompt = get_api_prompt("location_user_prompt").format(
            street=street,
            city=city,
            poi_name=poi_name,
            poi_address=poi_address,
        )

        payload = {
            "model": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 500,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        result = await deepseek_request(payload, http_client=http_client)
        if not result.startswith("Error:"):
            return result

        logger.warning(
            f"Failed with model deepseek-chat, trying next model if available"
        )

        models = [
            "deepseek-chat-v1",
            "deepseek-coder-33b-instruct",
            "deepseek-llm-67b-chat",
        ]

        for model in models:
            payload = {
                "model": model,
                "temperature": 0.7,
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            }

            result = await deepseek_request(payload, http_client=http_client)
            if not result.startswith("Error:"):
                return result

            logger.warning(f"Failed with model {model}, trying next model if available")

        return result

    except Exception as e:
        error_msg = f"Exception in DeepSeek location info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"Error: {error_msg}"


async def yandex_speechkit_tts(text: str, http_client=None, lang: str = "en") -> bytes:
    """Convert text to speech using Yandex SpeechKit."""
    try:
        if not http_client:
            http_client = await get_http_client()

        YA_SPEECHKIT_API_KEY = _get_api_key("YA_SPEECHKIT_API_KEY")
        if not YA_SPEECHKIT_API_KEY:
            logger.error(get_api_message("yandex_api_key_error"))
            return None

        # Map language codes to Yandex voice models and language codes
        voice_config = {
            "en": {"voice": "john", "lang": "en-US"},
            "ru": {"voice": "filipp", "lang": "ru-RU"},
        }

        # Get voice configuration based on language
        config = voice_config.get(
            lang, voice_config["en"]
        )  # Default to English if language not supported

        headers = {
            "Authorization": f"Api-Key {YA_SPEECHKIT_API_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "text": text,
            "lang": config["lang"],  # Use proper language code
            "voice": config["voice"],
            "emotion": "good",
            "format": "mp3",
            "speed": "1.0",
            "folderId": os.getenv("YA_CATALOG_ID", "b1gjn47rcuokgs8tfom5"),
        }

        url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

        response = await http_client.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.content
        else:
            logger.error(
                f"SpeechKit TTS error: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        logger.error(f"Exception in SpeechKit TTS: {str(e)}", exc_info=True)
        return None
