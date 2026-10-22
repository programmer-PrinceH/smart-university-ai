"""Python Assistant: explain, debug and improve Python code."""

import re
from collections.abc import Iterator

from ai.llm import stream_chat
from ai.prompts import PYTHON_SYSTEM_PROMPT
from config.settings import CHAT_HISTORY_LIMIT, PYTHON_MAX_TOKENS, PYTHON_TEMPERATURE

TASKS = {
    "Debug this error": "Debug the problem below. Follow your standard error-help format.",
    "Explain this code": "Explain what this code does, step by step.",
    "Improve this code": "Improve this code (readability, correctness, good practice) and explain each change.",
}


def _fence(text: str) -> str:
    """A code fence longer than any run of backticks inside the text."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def build_code_request(task: str, code: str, error: str = "") -> str:
    """Turn the code/error form into one clear message for the assistant."""
    code, error = code.strip(), error.strip()
    if not code and not error:
        raise ValueError("Paste some code or an error message first.")

    parts = [TASKS.get(task, TASKS["Debug this error"])]
    if code:
        fence = _fence(code)
        parts.append(f"My code:\n{fence}python\n{code}\n{fence}")
    if error:
        fence = _fence(error)
        parts.append(f"The error message:\n{fence}text\n{error}\n{fence}")
    return "\n\n".join(parts)


def build_messages(history: list[dict]) -> list[dict]:
    """System prompt + the most recent messages (the conversation memory)."""
    recent = history[-CHAT_HISTORY_LIMIT:]
    return [{"role": "system", "content": PYTHON_SYSTEM_PROMPT}, *recent]


def reply_stream(history: list[dict]) -> Iterator[str]:
    """Stream the assistant's answer to the conversation."""
    return stream_chat(
        build_messages(history),
        temperature=PYTHON_TEMPERATURE,
        max_tokens=PYTHON_MAX_TOKENS,
    )
