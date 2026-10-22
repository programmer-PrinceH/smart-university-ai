"""Shared test helpers: isolated storage, a fake LLM, fake embeddings, test PDFs.

Tests never call the real LLM or download the embedding model. They check OUR
code (parsing, validation, retrieval, storage, UI flow). Real model quality is
measured by evaluation/evaluator.py, not by these tests.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import the modules first so fixtures can patch their attributes
import ai.llm  # noqa: E402
import ai.rag  # noqa: E402
import ai.vector_store  # noqa: E402
import database.database  # noqa: E402
import documents.loader  # noqa: E402
import documents.summarizer  # noqa: E402
import evaluation.evaluator  # noqa: E402
from tests.helpers import DB_PAGES, fake_embed, make_pdf  # noqa: E402

@pytest.fixture
def storage(tmp_path, monkeypatch):
    """Point every storage location at a temporary folder."""
    monkeypatch.setattr(documents.loader, "UPLOADS_DIR", tmp_path / "uploads")
    monkeypatch.setattr(documents.loader, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(documents.loader, "SUMMARIES_DIR", tmp_path / "summaries")
    monkeypatch.setattr(documents.summarizer, "SUMMARIES_DIR", tmp_path / "summaries")
    monkeypatch.setattr(database.database, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(evaluation.evaluator, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(ai.vector_store, "VECTOR_DIR", tmp_path / "vectors")
    ai.vector_store._collection.cache_clear()
    database.database.init_db()
    yield tmp_path
    ai.vector_store._collection.cache_clear()


@pytest.fixture
def fake_embeddings(monkeypatch):
    monkeypatch.setattr(ai.rag, "embed_texts", lambda texts: [fake_embed(t) for t in texts])
    monkeypatch.setattr(ai.rag, "embed_query", fake_embed)


class FakeLLM:
    """Stands in for the API client. Set .handler to control the answers."""

    def __init__(self):
        self.calls: list[dict] = []
        self.handler = lambda messages, **kwargs: "OK"
        self.error: Exception | None = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        extras = {k: v for k, v in kwargs.items() if k != "messages"}
        text = self.handler(kwargs["messages"], **extras)
        if kwargs.get("stream"):
            pieces = [text[i : i + 12] for i in range(0, len(text), 12)] or [""]
            return iter(
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=p))])
                for p in pieces
            )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
        )


@pytest.fixture
def fake_llm(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(ai.llm, "get_client", lambda: llm)
    return llm


@pytest.fixture
def db_doc(storage, fake_embeddings):
    """A processed and indexed three-page database-notes document."""
    from documents.processor import process_pdf

    record, _ = process_pdf(make_pdf(DB_PAGES), "Database_Notes.pdf")
    ai.rag.index_document(record)
    return record
