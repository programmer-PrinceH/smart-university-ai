"""Left sidebar: brand, new chat, navigation, saved conversations, profile."""

import html
import logging
import sqlite3
from datetime import date, datetime, timedelta

import streamlit as st

from config.settings import (
    APP_NAME,
    APP_TAGLINE,
    NAV_ITEMS,
    USER_FULL_NAME,
    USER_SUBTITLE,
)
from database import database as db
from ui.icons import icon
from ui.components import (
    delete_conversation,
    empty_state,
    navigate,
    new_chat,
    open_conversation,
)

logger = logging.getLogger(__name__)

GROUP_ORDER = ["Today", "Yesterday", "Last 7 days", "Earlier"]
SIDEBAR_CONVERSATIONS = 12


def _group_label(updated_at: str) -> str:
    try:
        day = datetime.fromisoformat(updated_at).date()
    except ValueError:
        return "Earlier"
    today = date.today()
    if day == today:
        return "Today"
    if day == today - timedelta(days=1):
        return "Yesterday"
    if today - day <= timedelta(days=7):
        return "Last 7 days"
    return "Earlier"


def _short(title: str, limit: int = 26) -> str:
    return title if len(title) <= limit else title[: limit - 1].rstrip() + "…"


def _render_conversations(active_id: int | None) -> None:
    try:
        conversations = db.list_conversations(SIDEBAR_CONVERSATIONS)
    except sqlite3.Error:
        logger.exception("Could not list conversations")
        conversations = []

    if not conversations:
        empty_state("No conversations yet", "Start a chat and it will appear here.")
        return

    groups: dict[str, list[dict]] = {}
    for conversation in conversations:
        groups.setdefault(_group_label(conversation["updated_at"]), []).append(conversation)

    for label in GROUP_ORDER:
        if label not in groups:
            continue
        st.markdown(f"<div class='side-group'>{label}</div>", unsafe_allow_html=True)
        for conversation in groups[label]:
            cid = conversation["id"]
            key_prefix = "convopy" if conversation["mode"] == "python" else "convo"
            open_col, delete_col = st.columns([6, 1])
            with open_col:
                st.button(
                    _short(conversation["title"]),
                    key=f"{key_prefix}_{cid}",
                    on_click=open_conversation,
                    args=(cid, conversation["mode"]),
                )
            with delete_col:
                st.button(
                    "Delete",
                    key=f"delc_{cid}",
                    on_click=delete_conversation,
                    args=(cid,),
                    help="Delete this conversation",
                )
            if cid == active_id:
                st.markdown(
                    f"<style>.st-key-{key_prefix}_{cid} button {{"
                    "background: var(--accent-soft) !important;"
                    "color: var(--accent) !important;}</style>",
                    unsafe_allow_html=True,
                )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f"<div class='brand'><div class='brand-logo'>{icon('cap')}</div>"
            f"<div><div class='brand-name'>{APP_NAME}</div>"
            f"<div class='brand-sub'>{APP_TAGLINE}</div></div></div>",
            unsafe_allow_html=True,
        )

        st.button("New Chat", key="new_chat", on_click=new_chat)
        st.write("")

        # Navigation buttons
        active_page = st.session_state.page
        for item in NAV_ITEMS:
            st.button(
                item["page"],
                key=f"nav_{item['id']}",
                on_click=navigate,
                args=(item["page"],),
            )
            # Highlight the page the user is currently on
            if item["page"] == active_page:
                st.markdown(
                    f"<style>.st-key-nav_{item['id']} button {{"
                    "background: var(--accent-soft) !important;"
                    "color: var(--accent) !important; font-weight: 600 !important;}"
                    "</style>",
                    unsafe_allow_html=True,
                )

        st.markdown("<div class='side-label'>Recent Conversations</div>", unsafe_allow_html=True)
        chats = st.session_state.chats
        active_id = None
        if active_page == "Chat":
            active_id = chats["chat"]["id"]
        elif active_page == "Python Assistant":
            active_id = chats["python"]["id"]
        _render_conversations(active_id)

        st.write("")
        st.toggle("Dark mode", key="dark_mode")

        initials = "".join(word[0] for word in USER_FULL_NAME.split()[:2]).upper()
        st.markdown(
            f"<div class='profile'><div class='avatar'>{html.escape(initials)}</div>"
            f"<div><div class='profile-name'>{html.escape(USER_FULL_NAME)}</div>"
            f"<div class='profile-sub'>{USER_SUBTITLE}</div></div></div>",
            unsafe_allow_html=True,
        )
