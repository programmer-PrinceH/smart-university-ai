"""Documents page: upload PDFs, index them for search, then Ask / Summarize."""

import html
import logging

import streamlit as st

from ai.embeddings import EmbeddingError
from ai.rag import index_document, retrieve
from ai.vector_store import VectorStoreError, count_chunks, delete_document_chunks
from documents.loader import DocumentError, delete_document, list_documents
from documents.processor import process_pdf
from ui.components import empty_state
from ui.icons import icon
from ui.document_qa_ui import render_ask
from ui.summary_ui import render_summarize

logger = logging.getLogger(__name__)

DOC_MODES = ["Library", "Ask", "Summarize"]


def _select(doc_id: str) -> None:
    st.session_state.selected_doc = doc_id


def _remove(doc_id: str) -> None:
    delete_document(doc_id)
    try:
        delete_document_chunks(doc_id)
    except VectorStoreError:
        logger.warning("Could not remove vectors for %s", doc_id)
    if st.session_state.get("selected_doc") == doc_id:
        st.session_state.selected_doc = None


def _handle_upload(uploaded) -> None:
    """Process a newly uploaded file (only once per upload)."""
    signature = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.get("last_upload") == signature:
        return
    st.session_state.last_upload = signature

    with st.spinner("Reading your document..."):
        try:
            record, is_new = process_pdf(uploaded.getvalue(), uploaded.name)
        except DocumentError as error:
            st.error(str(error))
            return
        except Exception:  # unexpected: log it, show a clean message
            logger.exception("PDF processing failed")
            st.error("Something went wrong while reading this file. Please try another PDF.")
            return

    st.session_state.selected_doc = record["doc_id"]
    if is_new:
        st.success(f"{record['name']} was read successfully ({record['page_count']} pages).")
    else:
        st.info("This document was already uploaded, so the saved version is used.")


def _ensure_indexed(documents: list[dict]) -> dict[str, int]:
    """Index any document that is not searchable yet. Returns {doc_id: chunk_count}."""
    try:
        pending = [d for d in documents if count_chunks(d["doc_id"]) == 0]
        if pending:
            with st.spinner("Preparing documents for search... the first time can take a minute."):
                for doc in pending:
                    index_document(doc)
        return {d["doc_id"]: count_chunks(d["doc_id"]) for d in documents}
    except (EmbeddingError, VectorStoreError) as error:
        st.error(str(error))
    except Exception:
        logger.exception("Indexing failed")
        st.error("Something went wrong while preparing your documents for search.")
    return {d["doc_id"]: 0 for d in documents}


def _render_doc_card(doc: dict, is_selected: bool, chunks: int) -> None:
    doc_id = doc["doc_id"]
    with st.container(key=f"doc_{doc_id}"):
        info, select_col, delete_col = st.columns([6, 1.6, 1])
        with info:
            name = html.escape(doc["name"])  # never put raw file names into HTML
            pill = (
                f"<span class='pill-ready'>{icon('check-circle')}Ready</span>"
                if chunks
                else f"<span class='pill-ready pill-warn'>{icon('alert')}Not ready</span>"
            )
            st.markdown(
                f"<div class='doc-name'>{icon('file')}{name}{pill}</div>"
                f"<div class='doc-meta'>{doc['page_count']} pages • {chunks} chunks • "
                f"{doc['uploaded_at'][:10]}</div>",
                unsafe_allow_html=True,
            )
        with select_col:
            st.button(
                "Selected" if is_selected else "Select",
                key=f"select_{doc_id}",
                on_click=_select,
                args=(doc_id,),
                disabled=is_selected,
            )
        with delete_col:
            st.button("Delete", key=f"delete_{doc_id}", on_click=_remove, args=(doc_id,),
                      help="Delete this document")
    if is_selected:
        st.markdown(
            f"<style>.st-key-doc_{doc_id} {{ border-color: var(--accent) !important; }}</style>",
            unsafe_allow_html=True,
        )


def _render_preview(doc: dict) -> None:
    """Let the user check that the text was extracted correctly."""
    with st.expander("Preview extracted text", expanded=False):
        page_number = st.number_input(
            "Page", min_value=1, max_value=doc["page_count"], value=1, step=1,
            key=f"preview_page_{doc['doc_id']}",
        )
        text = doc["pages"][page_number - 1]["text"]
        st.text_area(
            "Extracted text", value=text or "(No text on this page)", height=240,
            disabled=True, label_visibility="collapsed",
        )


def _render_search_test(doc: dict) -> None:
    """Check retrieval on its own (no LLM): which chunks and pages are found."""
    with st.expander("Test retrieval", expanded=False):
        query = st.text_input(
            "Search this document",
            key=f"search_{doc['doc_id']}",
            placeholder="e.g. What is normalization?",
        )
        if not query.strip():
            st.caption("Type a question to see which chunks and pages are found.")
            return
        try:
            with st.spinner("Searching..."):
                results = retrieve(query, doc_ids=[doc["doc_id"]])
        except (EmbeddingError, VectorStoreError) as error:
            st.error(str(error))
            return
        if not results:
            st.info("No matching text was found.")
            return
        for rank, hit in enumerate(results, start=1):
            st.markdown(f"**{rank}. Page {hit['page']}** · similarity {hit['score']:.2f}")
            preview = hit["text"][:450] + ("..." if len(hit["text"]) > 450 else "")
            st.text(preview)


def _render_library() -> None:
    st.caption("Upload your lecture notes as a PDF. Files stay on this computer.")

    uploaded = st.file_uploader("Upload a PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded is None:
        st.session_state.last_upload = None  # allows re-uploading the same file later
    else:
        _handle_upload(uploaded)

    st.markdown("<div class='section-title'>Your documents</div>", unsafe_allow_html=True)
    documents = list_documents()
    if not documents:
        empty_state("No documents yet", "Upload a PDF above to get started.")
        return

    counts = _ensure_indexed(documents)
    selected_id = st.session_state.get("selected_doc")
    for doc in documents:
        _render_doc_card(doc, doc["doc_id"] == selected_id, counts.get(doc["doc_id"], 0))

    selected = next((d for d in documents if d["doc_id"] == selected_id), None)
    if selected:
        _render_preview(selected)
        if counts.get(selected["doc_id"], 0):
            _render_search_test(selected)


def render_documents() -> None:
    st.markdown("## Documents")
    mode = st.radio(
        "View",
        DOC_MODES,
        horizontal=True,
        label_visibility="collapsed",
        key="doc_mode",  # bound to session state so cards can switch the view
    )

    if mode == "Ask":
        render_ask()
    elif mode == "Summarize":
        render_summarize()
    else:
        _render_library()
