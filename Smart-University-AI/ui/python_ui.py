"""Python Assistant page: chat with a code/error form for structured requests."""

import streamlit as st

from config.settings import MAX_CODE_CHARS
from features.python_assistant import TASKS, build_code_request, reply_stream
from ui.chat_ui import render_conversation
from ui.components import new_chat


def _render_code_form(has_messages: bool) -> None:
    with st.expander("Paste code and/or an error message", expanded=not has_messages):
        task = st.radio("What do you need?", list(TASKS), horizontal=True, key="py_task")
        code = st.text_area("Python code", height=170, key="py_code",
                            placeholder="Paste your code here...")
        error = st.text_area("Error message (optional)", height=90, key="py_error",
                             placeholder="Paste the error / traceback here...")
        if st.button("Send to assistant", type="primary", key="py_send"):
            if len(code) > MAX_CODE_CHARS or len(error) > MAX_CODE_CHARS:
                st.warning(f"That is too long. The limit is {MAX_CODE_CHARS:,} characters.")
            elif not code.strip() and not error.strip():
                st.warning("Paste some code or an error message first.")
            else:
                st.session_state.py_pending = build_code_request(task, code, error)
                st.rerun()


def render_python() -> None:
    title_col, new_col = st.columns([5, 1.4])
    title_col.markdown("## Python Assistant")
    new_col.button("New conversation", key="py_new", on_click=new_chat, args=("python",))

    messages = st.session_state.chats["python"]["messages"]
    _render_code_form(has_messages=bool(messages))
    render_conversation(
        mode="python",
        stream_fn=reply_stream,
        pending_key="py_pending",
        placeholder="Ask a Python question, or describe your problem...",
        empty_title="Learn, debug and write Python",
        empty_text="Paste code and an error above, or ask a question below. "
        "Corrected code appears with syntax highlighting.",
    )
