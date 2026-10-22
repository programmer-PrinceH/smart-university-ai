import pytest

from ai.prompts import PYTHON_SYSTEM_PROMPT
from features.python_assistant import build_code_request, build_messages, reply_stream


def test_request_contains_task_code_and_error():
    text = build_code_request("Debug this error", "print(x)", "NameError: name 'x' is not defined")
    assert "Debug the problem" in text
    assert "```python\nprint(x)\n```" in text
    assert "NameError" in text


def test_code_only_and_error_only_are_allowed():
    assert "My code" in build_code_request("Explain this code", "a = 1")
    assert "The error message" in build_code_request("Debug this error", "", "ValueError")


def test_empty_request_is_refused():
    with pytest.raises(ValueError):
        build_code_request("Debug this error", "  ", " ")


def test_code_containing_backticks_cannot_break_the_fence():
    code = 'text = """\n```\nnested\n```\n"""'
    request = build_code_request("Explain this code", code)
    assert "````python" in request  # a longer fence than the three backticks inside


def test_system_prompt_requires_the_five_debugging_sections():
    for heading in (
        "What the error means",
        "Why it happened",
        "How to fix it",
        "Corrected code",
        "Explanation of the correction",
    ):
        assert heading in PYTHON_SYSTEM_PROMPT


def test_messages_are_limited_and_start_with_system_prompt():
    history = [{"role": "user", "content": str(i)} for i in range(50)]
    messages = build_messages(history)
    assert messages[0]["role"] == "system"
    assert len(messages) == 21


def test_reply_stream_uses_python_settings(fake_llm):
    fake_llm.handler = lambda m, **k: "Use a list."
    text = "".join(reply_stream([{"role": "user", "content": "hi"}]))
    assert text == "Use a list."
    assert fake_llm.calls[0]["temperature"] == 0.3
