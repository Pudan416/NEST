import os
import asyncio
import httpx
from app import logger
from app.texts import API_MESSAGES

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


async def deepseek_request(payload, max_retries=3):
    url = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_API_KEY = _get_api_key("DEEPSEEK_API_KEY")

    if not DEEPSEEK_API_KEY:
        return API_MESSAGES['deepseek_api_key_error']

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    for attempt in range(max_retries):
        try:
            client = await get_http_client()
            logger.debug(f"Sending request to DeepSeek API (attempt {attempt+1}/{max_retries})")

            response = await client.post(url, headers=headers, json=payload)
            logger.debug(f"DeepSeek API response status: {response.status_code}")

            if response.status_code == 401:
                logger.error("Authentication error: Invalid API key")
                return API_MESSAGES['invalid_api_key']

            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    retry_after = int(response.headers.get("retry-after", 1))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    return API_MESSAGES['rate_limit_exceeded']

            elif response.status_code == 200:
                response_data = response.json()

                if "choices" in response_data and response_data["choices"]:
                    message = response_data["choices"][0].get("message", {})
                    content = message.get("content", "")
                    if content:
                        return content
                    else:
                        logger.error("No content found in DeepSeek response")
                        return API_MESSAGES['no_content']
                else:
                    logger.error(f"Unexpected response format: {response_data}")
                    return API_MESSAGES['unexpected_format']
            else:
                error_msg = f"API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                return f"Error: {error_msg}"

        except httpx.ConnectTimeout:
            logger.error(f"Connection timeout to DeepSeek API (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff
                continue
            return API_MESSAGES['connection_timeout']

        except httpx.ReadTimeout:
            logger.error(f"Read timeout from DeepSeek API (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            return API_MESSAGES['read_timeout']

        except Exception as e:
            error_msg = f"Exception in DeepSeek API request: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
                continue
            return f"Error: {error_msg}"

    return API_MESSAGES['multiple_failures']


async def test_deepseek_connection():
    simple_payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": API_MESSAGES['deepseek_test_prompt']}],
        "max_tokens": 10,
    }
    result = await deepseek_request(simple_payload)
    logger.info(f"DeepSeek connection test result: {result}")
    return result


async def translate_to_english(text: str):
    if (
        not text
        or text.strip() == ""
        or text == API_MESSAGES['address_not_specified']
        or text == API_MESSAGES['address_not_available']
    ):
        return text

    payload = {
        "model": "deepseek-chat",
        "temperature": 0.3,
        "max_tokens": 500,
        "messages": [
            {
                "role": "system",
                "content": API_MESSAGES['translator_system_prompt'],
            },
            {"role": "user", "content": API_MESSAGES['translate_prompt'].format(text=text)},
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
    original_poi_name: str = None,
):
    context = (
        f"Original name: {original_poi_name}\n"
        if original_poi_name and original_poi_name != poi_name
        else ""
    )

    if not all([city, poi_name]):
        return API_MESSAGES['insufficient_info']

    models = [
        "deepseek-chat",
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
                    "content": API_MESSAGES['location_system_prompt'].format(
                        city=city, poi_name=poi_name, poi_address=poi_address, context=context
                    ),
                },
                {
                    "role": "user",
                    "content": API_MESSAGES['location_user_prompt'].format(
                        street=street, city=city, poi_name=poi_name, poi_address=poi_address
                    ),
                },
            ],
        }

        result = await deepseek_request(payload)
        if not result.startswith("Error:"):
            return result

        logger.warning(f"Failed with model {model}, trying next model if available")

    return result


async def yandex_speechkit_tts(text: str):
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

    YA_SPEECHKIT_API_KEY = _get_api_key("YA_SPEECHKIT_API_KEY")
    if not YA_SPEECHKIT_API_KEY:
        logger.error("YA_SPEECHKIT_API_KEY not found in environment variables")
        return None

    headers = {"Authorization": f"Api-Key {YA_SPEECHKIT_API_KEY}"}
    data = {
        "text": text,
        "lang": "en-US",
        "voice": "john",
        "format": "mp3",
        "folderId": os.getenv("YA_CATALOG_ID", "b1gjn47rcuokgs8tfom5"),
    }

    try:
        client = await get_http_client()
        response = await client.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"SpeechKit TTS error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception in SpeechKit TTS: {str(e)}", exc_info=True)
        return None