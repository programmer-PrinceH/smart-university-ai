"""Smart University AI: application entry point."""

import streamlit as st

from config.settings import APP_NAME
from database.database import init_db
from ui.chat_ui import render_chat, render_home, render_placeholder
from ui.documents_ui import render_documents
from ui.python_ui import render_python
from ui.quiz_ui import render_quiz
from ui.sidebar import render_sidebar
from ui.styles import apply_styles

# Must be the first Streamlit command
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_state() -> None:
    """Create the session values the app needs on first load."""
    st.session_state.setdefault("page", "Home")
    st.session_state.setdefault("dark_mode", False)
    st.session_state.setdefault("pending_prompt", None)  # message typed on Home
    st.session_state.setdefault("py_pending", None)  # request built by the code form
    st.session_state.setdefault(
        "chats",
        {
            "chat": {"id": None, "messages": []},
            "python": {"id": None, "messages": []},
        },
    )
    st.session_state.setdefault("selected_doc", None)  # the chosen document ID
    st.session_state.setdefault("doc_mode", "Library")  # Documents page view
    st.session_state.setdefault("doc_messages", [])  # Ask My Documents conversation
    st.session_state.setdefault("quiz", None)  # the quiz in progress


def main() -> None:
    init_db()
    init_state()
    apply_styles("dark" if st.session_state.dark_mode else "light")
    render_sidebar()

    page = st.session_state.page
    if page == "Home":
        render_home()
    elif page == "Chat":
        render_chat()
    elif page == "Documents":
        render_documents()
    elif page == "Quiz":
        render_quiz()
    elif page == "Python Assistant":
        render_python()
    else:
        render_placeholder(page)


main()
