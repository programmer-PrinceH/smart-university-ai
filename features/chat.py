"""AI Chat feature: prepares the conversation and asks the model."""

from collections.abc import Iterator

from ai.llm import stream_chat
from ai.prompts import CHAT_SYSTEM_PROMPT
from config.settings import CHAT_HISTORY_LIMIT


def build_messages(history: list[dict]) -> list[dict]:
    """System prompt + the most recent messages (the conversation memory)."""
    recent = history[-CHAT_HISTORY_LIMIT:]
    return [{"role": "system", "content": CHAT_SYSTEM_PROMPT}, *recent]


def reply_stream(history: list[dict]) -> Iterator[str]:
    """Return the model's answer to the conversation as a stream of text."""
    return stream_chat(build_messages(history))
