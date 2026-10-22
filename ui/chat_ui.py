"""Home screen and the shared conversation view (AI Chat, Python Assistant)."""

import html
import logging
import re
import sqlite3
from collections.abc import Callable, Iterator

import streamlit as st

from ai.llm import LLMError
from config.settings import FEATURES, MAX_MESSAGE_CHARS, USER_NAME
from database import database as db
from documents.loader import list_documents
from features.chat import reply_stream as chat_stream
from ui.components import empty_state, feature_card, new_chat, open_document
from ui.icons import icon

logger = logging.getLogger(__name__)


def _safe_db(action: Callable, *args):
    """Run a database action. A database problem must never break the chat."""
    try:
        return action(*args)
    except sqlite3.Error:
        logger.exception("Database error")
        return None


def _make_title(prompt: str) -> str:
    """A short conversation title taken from the first message."""
    first_line = re.sub(r"\s+", " ", prompt.splitlines()[0] if prompt.strip() else "").strip()
    return (first_line[:50].rstrip() + "…") if len(first_line) > 50 else first_line or "New chat"


def render_responsible_ai() -> None:
    with st.expander("Using this assistant responsibly"):
        st.markdown(
            "- **AI can be wrong.** Answers about your documents show the page they came "
            "from, so check the source. General answers should be double-checked.\n"
            "- **Your files stay on this computer.** Documents, search data and "
            "conversations are stored locally. Only the text of your question and the "
            "few passages needed to answer it are sent to the AI service.\n"
            "- **Learn, don't just copy.** This is a study tool. Use the explanations and "
            "quizzes to understand the material, and follow your university's rules on AI "
            "use for graded work."
        )


def render_home() -> None:
    st.markdown(
        f"<div class='hero'><div class='hero-logo'>{icon('cap')}</div>"
        f"<div class='hero-title'>Hello, {html.escape(USER_NAME)} 👋</div>"
        "<div class='hero-sub'>How can I help you today?</div></div>",
        unsafe_allow_html=True,
    )

    # Five cards: three on the first row, two on the second
    for row in (FEATURES[:3], FEATURES[3:]):
        columns = st.columns(3)
        for column, feature in zip(columns, row):
            with column:
                feature_card(feature)

    st.markdown("<div class='section-title'>Recent documents</div>", unsafe_allow_html=True)
    documents = list_documents()[:4]
    if not documents:
        empty_state("No documents yet", "Upload a PDF in Documents and it will appear here.")
    else:
        for column, doc in zip(st.columns(len(documents)), documents):
            with column, st.container(key=f"doc_home_{doc['doc_id']}"):
                st.markdown(
                    f"<div class='doc-name'>{icon('file')}{html.escape(doc['name'])}</div>"
                    f"<div class='doc-meta'>{doc['page_count']} pages</div>",
                    unsafe_allow_html=True,
                )
                st.button(
                    "Ask",
                    key=f"home_ask_{doc['doc_id']}",
                    on_click=open_document,
                    args=(doc["doc_id"], "Ask"),
                )

    render_responsible_ai()

    # Message composer (pinned to the bottom of the page)
    prompt = st.chat_input("Ask anything...")
    if prompt and prompt.strip():
        new_chat("chat")
        st.session_state.pending_prompt = prompt.strip()
        st.rerun()


def render_conversation(
    mode: str,
    stream_fn: Callable[[list[dict]], Iterator[str]],
    pending_key: str,
    placeholder: str,
    empty_title: str,
    empty_text: str,
) -> None:
    """Show a saved-conversation chat and answer new messages with streaming."""
    state = st.session_state.chats[mode]
    messages = state["messages"]

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # A message prepared elsewhere (home composer, code form) arrives as "pending"
    prompt = st.chat_input(placeholder)
    if st.session_state.get(pending_key):
        prompt = st.session_state[pending_key]
        st.session_state[pending_key] = None

    if not prompt or not prompt.strip():
        if not messages:
            empty_state(empty_title, empty_text)
        return
    prompt = prompt.strip()

    if len(prompt) > MAX_MESSAGE_CHARS:
        st.warning(
            f"That message is too long ({len(prompt):,} characters). "
            f"The limit is {MAX_MESSAGE_CHARS:,}."
        )
        return

    messages.append({"role": "user", "content": prompt})
    is_new_conversation = state["id"] is None
    if is_new_conversation:
        state["id"] = _safe_db(db.create_conversation, _make_title(prompt), mode)
    if state["id"] is not None:
        _safe_db(db.add_message, state["id"], "user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        box = st.empty()
        box.markdown("_Thinking..._")  # loading state
        reply = ""
        try:
            for piece in stream_fn(messages):
                reply += piece
                box.markdown(reply + "▌")  # typing cursor
        except LLMError as error:
            box.empty()
            st.error(str(error))
            return

        if not reply.strip():
            box.empty()
            st.warning("The AI returned an empty answer. Please try again.")
            return

        box.markdown(reply)
        messages.append({"role": "assistant", "content": reply})
        if state["id"] is not None:
            _safe_db(db.add_message, state["id"], "assistant", reply)

    if is_new_conversation and state["id"] is not None:
        st.rerun()  # refresh the sidebar so the new conversation appears


def render_chat() -> None:
    st.markdown("## AI Chat")
    render_conversation(
        mode="chat",
        stream_fn=chat_stream,
        pending_key="pending_prompt",
        placeholder="Ask anything...",
        empty_title="Start a conversation",
        empty_text="Ask a question below to begin.",
    )


def render_placeholder(page: str) -> None:
    """Shown only if a page name is unknown."""
    st.markdown(f"## {page}")
    empty_state(f"{page} is not available", "Choose another page from the sidebar.")
