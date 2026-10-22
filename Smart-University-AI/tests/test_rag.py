from ai import vector_store
from ai.rag import index_document, retrieve
from documents.processor import process_pdf
from features.document_qa import (
    build_context,
    extract_sources,
    find_relevant_chunks,
)
from ai.prompts import NOT_FOUND_MESSAGE

from tests.helpers import DB_PAGES, make_pdf


def test_index_stores_chunks_with_metadata(db_doc):
    assert vector_store.count_chunks(db_doc["doc_id"]) == 3
    hits = retrieve("normalization", top_k=3, doc_ids=[db_doc["doc_id"]])
    assert {h["doc_name"] for h in hits} == {"Database_Notes.pdf"}
    assert all(isinstance(h["page"], int) for h in hits)


def test_retrieval_returns_the_right_page_first(db_doc):
    doc_id = db_doc["doc_id"]
    assert retrieve("What is normalization?", 3, [doc_id])[0]["page"] == 1
    assert retrieve("primary key and foreign key", 3, [doc_id])[0]["page"] == 2
    assert retrieve("inner join versus left join", 3, [doc_id])[0]["page"] == 3


def test_scores_are_between_zero_and_one_and_sorted(db_doc):
    hits = retrieve("normalization redundancy", 3, [db_doc["doc_id"]])
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)
    assert all(-0.01 <= s <= 1.01 for s in scores)


def test_search_can_be_limited_to_one_document(db_doc, storage):
    other, _ = process_pdf(make_pdf(["Photosynthesis converts light into chemical energy."]), "Bio.pdf")
    index_document(other)
    only_bio = retrieve("normalization", 5, [other["doc_id"]])
    assert {h["doc_name"] for h in only_bio} == {"Bio.pdf"}
    both = retrieve("normalization", 5, [other["doc_id"], db_doc["doc_id"]])
    assert {h["doc_name"] for h in both} == {"Bio.pdf", "Database_Notes.pdf"}


def test_indexing_twice_does_not_duplicate(db_doc):
    index_document(db_doc)
    assert vector_store.count_chunks(db_doc["doc_id"]) == 3


def test_delete_chunks(db_doc):
    vector_store.delete_document_chunks(db_doc["doc_id"])
    assert vector_store.count_chunks(db_doc["doc_id"]) == 0


def test_empty_query_returns_nothing(db_doc):
    assert retrieve("   ", 3, [db_doc["doc_id"]]) == []


def test_threshold_filters_irrelevant_chunks(db_doc):
    ids = [db_doc["doc_id"]]
    relevant = find_relevant_chunks("normalization redundancy integrity", ids, 3, 0.2)
    assert relevant and relevant[0]["page"] == 1
    assert find_relevant_chunks("zebra giraffe savanna", ids, 3, 0.2) == []


def test_context_is_numbered_and_names_the_page():
    chunks = [
        {"doc_name": "A.pdf", "page": 4, "text": "alpha"},
        {"doc_name": "A.pdf", "page": 9, "text": "beta"},
    ]
    context = build_context(chunks)
    assert "[1] (Document: A.pdf, page 4)" in context
    assert "[2] (Document: A.pdf, page 9)" in context


def test_sources_come_from_chunk_metadata_not_from_the_ai():
    chunks = [
        {"doc_name": "A.pdf", "page": 4, "text": "alpha"},
        {"doc_name": "A.pdf", "page": 9, "text": "beta"},
    ]
    sources, verified = extract_sources("It is X [2]. Also page 99 [7].", chunks)
    assert verified
    assert [(s["doc_name"], s["page"]) for s in sources] == [("A.pdf", 9)]  # [7] ignored

    sources, verified = extract_sources("Combined [1, 2].", chunks)
    assert [s["page"] for s in sources] == [4, 9]


def test_uncited_answer_falls_back_and_is_marked_unverified():
    chunks = [{"doc_name": "A.pdf", "page": 4, "text": "alpha"}]
    sources, verified = extract_sources("An answer without citations.", chunks)
    assert not verified and [s["page"] for s in sources] == [4]


def test_not_found_answer_has_no_sources():
    chunks = [{"doc_name": "A.pdf", "page": 4, "text": "alpha"}]
    assert extract_sources(NOT_FOUND_MESSAGE, chunks) == ([], True)
