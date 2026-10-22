import pytest

from documents.chunker import chunk_document, split_text


def test_chunks_respect_size_and_have_overlap():
    sentences = [f"Sentence number {i} talks about databases." for i in range(60)]
    chunks = split_text(" ".join(sentences), chunk_size=300, overlap=80)
    assert len(chunks) > 3
    assert all(len(c) <= 301 for c in chunks)
    # the end of one chunk reappears at the start of the next (overlap)
    last_sentence = chunks[0].split(". ")[-1][:20]
    assert last_sentence in chunks[1]


def test_short_text_is_one_chunk():
    assert split_text("Just one short sentence.") == ["Just one short sentence."]


def test_empty_text_gives_no_chunks():
    assert split_text("   \n  ") == []


def test_very_long_unbroken_text_is_hard_split():
    chunks = split_text("x" * 5000, chunk_size=500, overlap=100)
    assert len(chunks) >= 10
    assert all(len(c) <= 501 for c in chunks)


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        split_text("text", chunk_size=100, overlap=100)


def test_chunk_document_keeps_page_numbers_and_ids():
    record = {
        "doc_id": "abc",
        "name": "Notes.pdf",
        "pages": [
            {"page": 1, "text": "First page text about normalization and keys."},
            {"page": 2, "text": ""},
            {"page": 3, "text": "Third page text about joins and indexes in SQL."},
        ],
    }
    chunks = chunk_document(record)
    assert [c["page"] for c in chunks] == [1, 3]
    assert chunks[0]["chunk_id"] == "abc_p1_c0"
    assert all(c["doc_name"] == "Notes.pdf" for c in chunks)


def test_tiny_fragments_are_dropped():
    record = {"doc_id": "d", "name": "n.pdf", "pages": [{"page": 1, "text": "Hi."}]}
    assert chunk_document(record) == []
