"""PDF text extraction and cleaning."""

import re
from datetime import datetime

import pymupdf

from config.settings import MAX_PDF_PAGES, MIN_TEXT_CHARS
from documents.loader import (
    DocumentError,
    load_record,
    make_doc_id,
    save_pdf,
    save_record,
    validate_pdf,
)


def clean_text(text: str) -> str:
    """Tidy raw PDF text so it is ready for chunking and embeddings."""
    text = text.replace("\x00", "")  # remove null characters
    text = re.sub(r"(\w)-\n(?=[a-z])", r"\1", text)  # join words split by a line break
    text = re.sub(r"^[ \t]*\d{1,3}[ \t]*$", "", text, flags=re.MULTILINE)  # page numbers
    text = re.sub(r"[ \t]+", " ", text)  # collapse repeated spaces
    text = re.sub(r" *\n *", "\n", text)  # trim spaces around line breaks
    text = re.sub(r"\n{3,}", "\n\n", text)  # at most one blank line
    return text.strip()


def extract_pages(pdf_bytes: bytes) -> list[dict]:
    """Read a PDF and return [{'page': 1, 'text': '...'}, ...]."""
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as error:
        raise DocumentError("This PDF could not be opened. The file may be damaged.") from error

    with doc:
        if doc.needs_pass:
            raise DocumentError("This PDF is password-protected. Remove the password and try again.")
        if doc.page_count == 0:
            raise DocumentError("This PDF has no pages.")
        if doc.page_count > MAX_PDF_PAGES:
            raise DocumentError(
                f"This PDF has {doc.page_count} pages. The limit is {MAX_PDF_PAGES} pages."
            )
        return [
            {"page": number, "text": clean_text(page.get_text("text"))}
            for number, page in enumerate(doc, start=1)
        ]


def process_pdf(data: bytes, filename: str) -> tuple[dict, bool]:
    """Validate, extract and store a PDF.

    Returns (record, is_new). is_new is False when this exact file was
    processed before, so we reuse the saved result instead of repeating the work.
    """
    validate_pdf(data)
    doc_id = make_doc_id(data)

    existing = load_record(doc_id)
    if existing:
        return existing, False

    pages = extract_pages(data)
    char_count = sum(len(page["text"]) for page in pages)
    if char_count < MIN_TEXT_CHARS:
        raise DocumentError(
            "No readable text was found. This PDF may contain scanned images. "
            "Please upload a text-based PDF."
        )

    save_pdf(doc_id, data)
    record = {
        "doc_id": doc_id,
        "name": filename,
        "page_count": len(pages),
        "char_count": char_count,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        "pages": pages,
    }
    save_record(record)
    return record, True
