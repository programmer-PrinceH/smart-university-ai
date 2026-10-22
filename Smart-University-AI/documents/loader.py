"""Validating, saving, listing and deleting uploaded documents."""

import hashlib
import json
from pathlib import Path

from config.settings import MAX_PDF_SIZE_MB, PROCESSED_DIR, SUMMARIES_DIR, UPLOADS_DIR


class DocumentError(Exception):
    """A document problem with a message that is safe to show to the user."""


def make_doc_id(data: bytes) -> str:
    """A short fingerprint of the file content: the same file always gets the same ID."""
    return hashlib.sha256(data).hexdigest()[:16]


def validate_pdf(data: bytes) -> None:
    """Basic checks before we try to read the file."""
    if not data:
        raise DocumentError("This file is empty.")
    if len(data) > MAX_PDF_SIZE_MB * 1024 * 1024:
        raise DocumentError(f"This file is too large. The limit is {MAX_PDF_SIZE_MB} MB.")
    if not data.startswith(b"%PDF"):
        raise DocumentError("This does not look like a valid PDF file.")


def save_pdf(doc_id: str, data: bytes) -> Path:
    """Store the original PDF locally, named by its ID (never by the user's file name)."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / f"{doc_id}.pdf"
    path.write_bytes(data)
    return path


def _record_path(doc_id: str) -> Path:
    return PROCESSED_DIR / f"{doc_id}.json"


def save_record(record: dict) -> None:
    """Store the extracted text and details of a document."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    _record_path(record["doc_id"]).write_text(
        json.dumps(record, ensure_ascii=False), encoding="utf-8"
    )


def load_record(doc_id: str) -> dict | None:
    """Load a stored document, or None if it doesn't exist or is damaged."""
    path = _record_path(doc_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_documents() -> list[dict]:
    """All processed documents, newest first."""
    if not PROCESSED_DIR.exists():
        return []
    records = []
    for path in PROCESSED_DIR.glob("*.json"):
        record = load_record(path.stem)
        if record:
            records.append(record)
    return sorted(records, key=lambda r: r["uploaded_at"], reverse=True)


def delete_document(doc_id: str) -> None:
    """Remove a document's PDF, extracted text and saved summary."""
    (UPLOADS_DIR / f"{doc_id}.pdf").unlink(missing_ok=True)
    _record_path(doc_id).unlink(missing_ok=True)
    (SUMMARIES_DIR / f"{doc_id}.json").unlink(missing_ok=True)
