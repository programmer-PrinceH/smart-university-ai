import pytest

from documents.loader import DocumentError, delete_document, load_record
from documents.processor import process_pdf
from documents.summarizer import build_sections, load_summary, summarize_document

from tests.helpers import make_pdf


def record(pages, text="Databases store data in tables. " * 5):
    return {
        "doc_id": "doc1",
        "name": "Notes.pdf",
        "pages": [{"page": p, "text": text} for p in range(1, pages + 1)],
    }


def test_sections_group_whole_pages_within_the_limit():
    sections = build_sections(record(10, "x" * 100), max_chars=350)
    assert [(s["start"], s["end"]) for s in sections] == [(1, 3), (4, 6), (7, 9), (10, 10)]
    assert all("--- Page" in s["text"] for s in sections)


def test_empty_pages_are_skipped():
    rec = record(3)
    rec["pages"][1]["text"] = ""
    sections = build_sections(rec)
    assert "Page 2" not in sections[0]["text"]


def test_short_document_is_summarised_with_one_call(storage, fake_llm):
    fake_llm.handler = lambda m, **k: "## Short overview\nA summary."
    result = summarize_document(record(2))
    assert result["method"] == "direct" and result["sections"] == 1
    assert len(fake_llm.calls) == 1
    assert result["summary"].startswith("## Short overview")


def test_long_document_uses_map_reduce(storage, fake_llm, monkeypatch):
    import documents.summarizer as summarizer

    monkeypatch.setattr(summarizer, "SUMMARY_SECTION_CHARS", 600)
    fake_llm.handler = lambda m, **k: "notes " * 20
    progress = []
    result = summarize_document(record(12, "y" * 200), lambda f, msg: progress.append((f, msg)))
    assert result["method"] == "map-reduce" and result["sections"] > 1
    assert len(fake_llm.calls) >= result["sections"] + 1  # notes per section + final summary
    assert progress[-1][0] == 1.0
    assert any("Reading section" in msg for _, msg in progress)


def test_summary_is_saved_and_reloaded(storage, fake_llm):
    fake_llm.handler = lambda m, **k: "Saved summary"
    summarize_document(record(1))
    assert load_summary("doc1")["summary"] == "Saved summary"
    assert load_summary("missing") is None


def test_deleting_a_document_removes_its_summary(storage, fake_llm):
    fake_llm.handler = lambda m, **k: "Summary text"
    rec, _ = process_pdf(make_pdf(["Databases store data in tables. " * 6]), "a.pdf")
    summarize_document(load_record(rec["doc_id"]))
    assert load_summary(rec["doc_id"]) is not None
    delete_document(rec["doc_id"])
    assert load_summary(rec["doc_id"]) is None


def test_document_without_text_is_refused(storage, fake_llm):
    with pytest.raises(DocumentError):
        summarize_document(record(2, ""))
