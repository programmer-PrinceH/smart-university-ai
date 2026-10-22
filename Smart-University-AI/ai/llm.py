"""Connection to the language model (any OpenAI-compatible API)."""

import logging
from collections.abc import Iterator
from functools import lru_cache

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
    OpenAI,
    RateLimitError,
)

from config.settings import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """An error whose message is safe to show to the user."""


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """Create the API client once and reuse it for every message."""
    if not LLM_API_KEY or LLM_API_KEY == "your_key_here":
        raise LLMError(
            "No API key found. Add your key to the .env file as LLM_API_KEY, "
            "then restart the app."
        )
    return OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        timeout=LLM_TIMEOUT,
        max_retries=LLM_MAX_RETRIES,
    )


def _friendly_error(error: Exception) -> LLMError:
    """Turn technical API errors into short, clear messages."""
    # Technical details go to the terminal (never the screen) to help debugging
    logger.warning("LLM request failed: %s: %s", type(error).__name__, error)

    if isinstance(error, AuthenticationError):
        return LLMError("The API key was rejected. Check LLM_API_KEY in your .env file.")
    if isinstance(error, RateLimitError):
        return LLMError("Too many requests right now. Please wait a moment and try again.")
    if isinstance(error, NotFoundError):
        return LLMError("The model was not found. Check LLM_MODEL in your .env file.")
    if isinstance(error, APITimeoutError):
        return LLMError("The AI took too long to answer. Please try again.")
    if isinstance(error, APIConnectionError):
        return LLMError("Cannot reach the AI service. Please check your internet connection.")
    if isinstance(error, APIStatusError):
        return LLMError(
            f"The AI service returned an error (code {error.status_code}). "
            "Check your key and model settings, then try again."
        )
    return LLMError("Something went wrong while contacting the AI. Please try again.")


def stream_chat(
    messages: list[dict],
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
) -> Iterator[str]:
    """Send messages to the model and yield the answer piece by piece."""
    client = get_client()
    try:
        stream = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except LLMError:
        raise
    except Exception as error:  # never show raw tracebacks to the user
        raise _friendly_error(error) from error


def complete(
    messages: list[dict],
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
) -> str:
    """Send messages and return the whole answer as one string (no streaming)."""
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except LLMError:
        raise
    except Exception as error:  # never show raw tracebacks to the user
        raise _friendly_error(error) from error

    if not response.choices:
        raise LLMError("The AI returned no answer. Please try again.")
    return (response.choices[0].message.content or "").strip()
