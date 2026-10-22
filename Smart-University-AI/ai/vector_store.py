"""ChromaDB storage: save chunks with metadata and search them by meaning."""

from functools import lru_cache

from config.settings import COLLECTION_NAME, VECTOR_DIR


class VectorStoreError(Exception):
    """A vector database problem with a message that is safe to show to the user."""


@lru_cache(maxsize=1)
def _collection():
    """Open the database once (it is saved on disk in vector_store/)."""
    try:
        import chromadb
        from chromadb.config import Settings

        VECTOR_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(VECTOR_DIR), settings=Settings(anonymized_telemetry=False)
        )
        return client.get_or_create_collection(name=COLLECTION_NAME)
    except Exception as error:
        raise VectorStoreError("The document search database could not be opened.") from error


def add_chunks(chunks: list[dict], embeddings: list[list[float]], batch: int = 500) -> None:
    """Store chunks, their vectors and their metadata (upsert = safe to repeat)."""
    collection = _collection()
    try:
        for start in range(0, len(chunks), batch):
            part = chunks[start : start + batch]
            collection.upsert(
                ids=[c["chunk_id"] for c in part],
                embeddings=embeddings[start : start + batch],
                documents=[c["text"] for c in part],
                metadatas=[
                    {
                        "doc_id": c["doc_id"],
                        "doc_name": c["doc_name"],
                        "page": c["page"],
                        "chunk_index": c["chunk_index"],
                    }
                    for c in part
                ],
            )
    except Exception as error:
        raise VectorStoreError("The document could not be saved for searching.") from error


def count_chunks(doc_id: str) -> int:
    """How many chunks of this document are stored (0 = not indexed yet)."""
    try:
        result = _collection().get(where={"doc_id": doc_id}, include=[])
        return len(result["ids"])
    except VectorStoreError:
        raise
    except Exception as error:
        raise VectorStoreError("The document search database could not be read.") from error


def delete_document_chunks(doc_id: str) -> None:
    try:
        _collection().delete(where={"doc_id": doc_id})
    except VectorStoreError:
        raise
    except Exception as error:
        raise VectorStoreError("The document could not be removed from search.") from error


def search(
    query_embedding: list[float], top_k: int, doc_ids: list[str] | None = None
) -> list[dict]:
    """Return the chunks closest in meaning to the question, with real sources."""
    where = None
    if doc_ids:
        where = {"doc_id": doc_ids[0]} if len(doc_ids) == 1 else {"doc_id": {"$in": doc_ids}}
    try:
        result = _collection().query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except VectorStoreError:
        raise
    except Exception as error:
        raise VectorStoreError("The search could not be completed.") from error

    hits = []
    for text, meta, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append(
            {
                "text": text,
                "doc_id": meta["doc_id"],
                "doc_name": meta["doc_name"],
                "page": meta["page"],
                # Chroma returns squared L2 distance. With normalised vectors,
                # cosine similarity = 1 - distance / 2.
                "score": 1 - distance / 2,
            }
        )
    return hits
