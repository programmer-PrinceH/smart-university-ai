import pymupdf
import pytest

import documents.processor as processor
from documents.loader import (
    DocumentError,
    delete_document,
    list_documents,
    load_record,
)
from documents.processor import clean_text, process_pdf

from tests.helpers import DB_PAGES, make_pdf


def test_clean_text_rules():
    raw = "Normal-\nization is   useful.\n\n\n\n12\nNext   line\x00 here"
    cleaned = clean_text(raw)
    assert "Normalization" in cleaned  # hyphenated line break joined
    assert "\n\n\n" not in cleaned  # blank lines limited
    assert "   " not in cleaned  # spaces collapsed
    assert "\n12\n" not in cleaned  # lone page number removed
    assert "\x00" not in cleaned


def test_process_pdf_extracts_pages_and_stores_record(storage):
    record, is_new = process_pdf(make_pdf(DB_PAGES), "Database_Notes.pdf")
    assert is_new
    assert record["page_count"] == 3
    assert "Normalization" in record["pages"][0]["text"]
    assert "primary key" in record["pages"][1]["text"].lower()
    assert load_record(record["doc_id"])["name"] == "Database_Notes.pdf"
    assert [d["doc_id"] for d in list_documents()] == [record["doc_id"]]


def test_same_file_is_not_processed_twice(storage):
    data = make_pdf(DB_PAGES)
    first, new_first = process_pdf(data, "a.pdf")
    second, new_second = process_pdf(data, "renamed.pdf")
    assert new_first and not new_second
    assert first["doc_id"] == second["doc_id"]
    assert len(list_documents()) == 1


def test_invalid_files_are_rejected_with_clean_messages(storage):
    with pytest.raises(DocumentError, match="empty"):
        process_pdf(b"", "x.pdf")
    with pytest.raises(DocumentError, match="valid PDF"):
        process_pdf(b"just some text, not a pdf", "x.pdf")
    with pytest.raises(DocumentError, match="damaged"):
        process_pdf(b"%PDF-1.4 this is broken", "x.pdf")


def test_pdf_without_text_is_rejected(storage):
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    with pytest.raises(DocumentError, match="No readable text"):
        process_pdf(data, "scanned.pdf")


def test_too_many_pages_is_rejected(storage, monkeypatch):
    monkeypatch.setattr(processor, "MAX_PDF_PAGES", 2)
    with pytest.raises(DocumentError, match="limit"):
        process_pdf(make_pdf(DB_PAGES), "long.pdf")


def test_too_large_file_is_rejected(storage, monkeypatch):
    import documents.loader as loader

    monkeypatch.setattr(loader, "MAX_PDF_SIZE_MB", 0)
    with pytest.raises(DocumentError, match="too large"):
        process_pdf(make_pdf(DB_PAGES), "big.pdf")


def test_delete_document_removes_files(storage):
    record, _ = process_pdf(make_pdf(DB_PAGES), "a.pdf")
    delete_document(record["doc_id"])
    assert list_documents() == []
    assert not any((storage / "uploads").glob("*.pdf"))
