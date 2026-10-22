import httpx
import openai
import pytest

import ai.llm as llm
from ai.llm import LLMError, complete, stream_chat
from features.chat import build_messages


def request():
    return httpx.Request("POST", "https://example.test/v1/chat/completions")


def status_error(cls, code):
    return cls("boom", response=httpx.Response(code, request=request()), body=None)


@pytest.mark.parametrize(
    "error, expected",
    [
        (status_error(openai.AuthenticationError, 401), "key was rejected"),
        (status_error(openai.RateLimitError, 429), "Too many requests"),
        (status_error(openai.NotFoundError, 404), "model was not found"),
        (openai.APITimeoutError(request=request()), "too long"),
        (openai.APIConnectionError(request=request()), "Cannot reach"),
        (status_error(openai.InternalServerError, 500), "code 500"),
        (RuntimeError("anything else"), "Something went wrong"),
    ],
)
def test_errors_become_friendly_messages(fake_llm, error, expected):
    fake_llm.error = error
    with pytest.raises(LLMError, match=expected) as caught:
        complete([{"role": "user", "content": "hi"}])
    assert "boom" not in str(caught.value)  # no technical details shown to the user

    with pytest.raises(LLMError, match=expected):
        list(stream_chat([{"role": "user", "content": "hi"}]))


def test_missing_key_gives_a_clear_message(monkeypatch):
    monkeypatch.setattr(llm, "LLM_API_KEY", "")
    llm.get_client.cache_clear()
    with pytest.raises(LLMError, match="No API key"):
        llm.get_client()
    monkeypatch.setattr(llm, "LLM_API_KEY", "your_key_here")
    llm.get_client.cache_clear()
    with pytest.raises(LLMError, match="No API key"):
        llm.get_client()
    llm.get_client.cache_clear()


def test_streaming_joins_the_pieces(fake_llm):
    fake_llm.handler = lambda m, **k: "Python is a programming language."
    pieces = list(stream_chat([{"role": "user", "content": "What is Python?"}]))
    assert len(pieces) > 1
    assert "".join(pieces) == "Python is a programming language."
    assert fake_llm.calls[0]["stream"] is True


def test_empty_choices_raise_a_clean_error(fake_llm, monkeypatch):
    from types import SimpleNamespace

    fake_llm.chat.completions.create = lambda **k: SimpleNamespace(choices=[])
    with pytest.raises(LLMError, match="no answer"):
        complete([{"role": "user", "content": "hi"}])


def test_chat_memory_sends_recent_history_with_system_prompt():
    history = [{"role": "user", "content": f"m{i}"} for i in range(30)]
    messages = build_messages(history)
    assert messages[0]["role"] == "system"
    assert [m["content"] for m in messages[1:]] == [f"m{i}" for i in range(10, 30)]
