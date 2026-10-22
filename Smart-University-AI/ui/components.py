"""Small reusable UI pieces and navigation helpers."""

import logging
import sqlite3

import streamlit as st

from database import database as db

logger = logging.getLogger(__name__)

MODE_PAGES = {"chat": "Chat", "python": "Python Assistant"}


def navigate(page: str, mode: str | None = None) -> None:
    """Switch to another page (and, for Documents, to a specific view)."""
    st.session_state.page = page
    if mode:
        st.session_state.doc_mode = mode


def open_document(doc_id: str, mode: str = "Ask") -> None:
    """Select a document and open it in the Documents page."""
    st.session_state.selected_doc = doc_id
    navigate("Documents", mode)


def new_chat(mode: str = "chat") -> None:
    """Start a fresh conversation in AI Chat ('chat') or Python Assistant ('python')."""
    st.session_state.chats[mode] = {"id": None, "messages": []}
    st.session_state.page = MODE_PAGES[mode]
    if mode == "chat":
        st.session_state.pending_prompt = None
    else:
        st.session_state.py_pending = None


def open_conversation(conversation_id: int, mode: str) -> None:
    """Load a saved conversation from the database and show it."""
    try:
        messages = db.get_messages(conversation_id)
    except sqlite3.Error:
        logger.exception("Could not load conversation %s", conversation_id)
        messages = []
    st.session_state.chats[mode] = {"id": conversation_id, "messages": messages}
    st.session_state.page = MODE_PAGES[mode]


def delete_conversation(conversation_id: int) -> None:
    """Delete a saved conversation (and clear it if it is open)."""
    try:
        db.delete_conversation(conversation_id)
    except sqlite3.Error:
        logger.exception("Could not delete conversation %s", conversation_id)
    for state in st.session_state.chats.values():
        if state["id"] == conversation_id:
            state["id"] = None
            state["messages"] = []


def feature_card(feature: dict) -> None:
    """Draw one feature card with an 'Open' button."""
    with st.container(key=f"card_{feature['id']}"):
        st.markdown(
            f"<div class='card-icon' style='background:{feature['tint']}'>{feature['icon']}</div>"
            f"<div class='card-title'>{feature['title']}</div>"
            f"<div class='card-desc'>{feature['description']}</div>",
            unsafe_allow_html=True,
        )
        st.button(
            "Open →",
            key=f"open_{feature['id']}",
            on_click=navigate,
            args=(feature["page"], feature.get("mode")),
        )


def empty_state(title: str, text: str) -> None:
    """A friendly box shown when there is nothing to display yet."""
    st.markdown(
        f"<div class='empty-state'><b>{title}</b>{text}</div>",
        unsafe_allow_html=True,
    )
