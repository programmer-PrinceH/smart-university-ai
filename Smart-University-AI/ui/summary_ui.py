"""Summarize view: pick a document and get a structured study summary."""

import logging
import re

import streamlit as st

from ai.llm import LLMError
from documents.loader import DocumentError, list_documents
from documents.summarizer import load_summary, summarize_document
from ui.components import empty_state

logger = logging.getLogger(__name__)

METHOD_LABELS = {"direct": "Direct summary", "map-reduce": "Chunk-based summary"}


def _render_summary(record: dict, summary: dict) -> None:
    with st.container(border=True):
        st.markdown(summary["summary"])

    label = METHOD_LABELS.get(summary["method"], summary["method"])
    st.caption(
        f"{label} · {summary['sections']} section(s) · {summary['model']} · "
        f"generated in {summary['seconds']:.1f} s"
    )

    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", record["name"].rsplit(".", 1)[0]) or "document"
    st.download_button(
        "Download summary (.md)",
        data=f"# Summary: {record['name']}\n\n{summary['summary']}\n",
        file_name=f"{stem}_summary.md",
        mime="text/markdown",
    )


def render_summarize() -> None:
    documents = list_documents()
    if not documents:
        empty_state("No documents yet", "Upload a PDF in Library first.")
        return

    by_id = {doc["doc_id"]: doc for doc in documents}
    ids = list(by_id)
    selected = st.session_state.get("selected_doc")
    index = ids.index(selected) if selected in ids else 0

    doc_id = st.selectbox(
        "Document to summarize",
        ids,
        index=index,
        format_func=lambda i: by_id[i]["name"],
    )
    record = by_id[doc_id]
    summary = load_summary(doc_id)

    st.caption(
        f"{record['page_count']} pages · long documents are summarised section by section."
    )
    if st.button("Regenerate summary" if summary else "Summarize document", type="primary"):
        bar = st.progress(0.0, text="Starting...")
        try:
            summary = summarize_document(
                record,
                progress=lambda fraction, message: bar.progress(
                    min(max(fraction, 0.0), 1.0), text=message
                ),
            )
        except (LLMError, DocumentError) as error:
            bar.empty()
            st.error(str(error))
            return
        except Exception:  # unexpected: log it, show a clean message
            logger.exception("Summarization failed")
            bar.empty()
            st.error("Something went wrong while summarising. Please try again.")
            return
        bar.empty()

    if summary:
        _render_summary(record, summary)
