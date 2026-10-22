import sys
import types

import pytest

import ai.embeddings as emb


@pytest.fixture(autouse=True)
def fresh_model_cache():
    emb.get_model.cache_clear()
    yield
    emb.get_model.cache_clear()


def test_missing_model_gives_a_clean_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)  # import fails
    with pytest.raises(emb.EmbeddingError, match="could not be loaded"):
        emb.embed_texts(["hello"])


def test_vectors_are_requested_normalised_and_the_model_is_loaded_once(monkeypatch):
    loads, encode_args = [], []

    class FakeArray(list):
        def tolist(self):
            return list(self)

    class FakeModel:
        def __init__(self, name):
            loads.append(name)

        def encode(self, texts, **kwargs):
            encode_args.append(kwargs)
            return FakeArray([[0.1, 0.2] for _ in texts])

    module = types.SimpleNamespace(SentenceTransformer=FakeModel)
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)

    assert emb.embed_texts(["a", "b"]) == [[0.1, 0.2], [0.1, 0.2]]
    assert emb.embed_query("c") == [0.1, 0.2]
    assert len(loads) == 1  # loaded once, reused
    assert loads[0] == "sentence-transformers/all-MiniLM-L6-v2"
    assert encode_args[0]["normalize_embeddings"] is True


def test_no_texts_means_no_model_load():
    assert emb.embed_texts([]) == []
