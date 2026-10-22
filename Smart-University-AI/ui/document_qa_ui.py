"""Ask My Documents: questions answered from uploaded PDFs, with real sources."""

import time

import streamlit as st

from ai.embeddings import EmbeddingError
from ai.llm import LLMError
from ai.prompts import NOT_FOUND_MESSAGE
from ai.vector_store import VectorStoreError, count_chunks
from documents.loader import list_documents
from features.document_qa import answer_stream, extract_sources, find_relevant_chunks
from ui.components import empty_state


def _clear_conversation() -> None:
    st.session_state.doc_messages = []


def _ready_documents() -> list[dict]:
    """Documents that are indexed and can be searched."""
    try:
        return [d for d in list_documents() if count_chunks(d["doc_id"]) > 0]
    except VectorStoreError as error:
        st.error(str(error))
        return []


def _render_sources(message: dict) -> None:
    sources = message.get("sources", [])
    if not sources:
        return
    title = (
        "Sources"
        if message.get("verified")
        else "Related pages (the AI did not cite a specific passage)"
    )
    st.markdown(f"**{title}**")
    for source in sources:
        st.markdown(f"**[{source['n']}]** `{source['doc_name']}` — Page {source['page']}")
    with st.expander("Show the passages used"):
        for source in sources:
            st.caption(f"[{source['n']}] {source['doc_name']} — Page {source['page']}")
            st.text(source["text"][:700])


def _render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            _render_sources(message)
            if message.get("elapsed"):
                st.caption(f"Answered in {message['elapsed']:.1f} s")


def render_ask() -> None:
    documents = _ready_documents()
    if not documents:
        empty_state(
            "No searchable documents yet",
            "Upload a PDF in Library and wait until it shows ✓ Ready.",
        )
        return

    names = {doc["doc_id"]: doc["name"] for doc in documents}
    options = ["__all__", *names]
    selected = st.session_state.get("selected_doc")
    index = options.index(selected) if selected in options else 0

    left, right = st.columns([5, 1])
    with left:
        scope = st.selectbox(
            "Ask about",
            options,
            index=index,
            format_func=lambda o: "All my documents" if o == "__all__" else names[o],
        )
    with right:
        st.write("")
        st.button("Clear chat", on_click=_clear_conversation)
    doc_ids = None if scope == "__all__" else [scope]

    messages = st.session_state.doc_messages
    if not messages:
        empty_state(
            "Ask anything about your notes",
            "Answers come only from your documents and show the page they came from.",
        )
    for message in messages:
        _render_message(message)

    question = st.chat_input("Ask a question about your documents...")
    if not question or not question.strip():
        return
    question = question.strip()

    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("_Searching your documents..._")
        started = time.perf_counter()
        try:
            chunks = find_relevant_chunks(question, doc_ids)
            if not chunks:
                reply, sources, verified = NOT_FOUND_MESSAGE, [], True
                placeholder.markdown(reply)
            else:
                placeholder.markdown("_Thinking..._")
                reply = ""
                for piece in answer_stream(question, chunks):
                    reply += piece
                    placeholder.markdown(reply + "▌")
                placeholder.markdown(reply)
                sources, verified = extract_sources(reply, chunks)
        except (LLMError, EmbeddingError, VectorStoreError) as error:
            placeholder.empty()
            st.error(str(error))
            return

        if not reply.strip():
            placeholder.empty()
            st.warning("The AI returned an empty answer. Please try again.")
            return

        message = {
            "role": "assistant",
            "content": reply,
            "sources": sources,
            "verified": verified,
            "elapsed": time.perf_counter() - started,
        }
        _render_sources(message)
        st.caption(f"Answered in {message['elapsed']:.1f} s")
        messages.append(message)
