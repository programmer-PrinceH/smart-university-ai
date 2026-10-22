"""RAG pipeline: indexing a document and retrieving relevant chunks."""

from ai import vector_store
from ai.embeddings import embed_query, embed_texts
from config.settings import TOP_K
from documents.chunker import chunk_document


def index_document(record: dict) -> int:
    """Chunk a stored document, embed the chunks and save them. Returns the chunk count."""
    chunks = chunk_document(record)
    if not chunks:
        return 0
    vectors = embed_texts([chunk["text"] for chunk in chunks])
    vector_store.add_chunks(chunks, vectors)
    return len(chunks)


def retrieve(query: str, top_k: int = TOP_K, doc_ids: list[str] | None = None) -> list[dict]:
    """Find the chunks most relevant to a question."""
    query = query.strip()
    if not query:
        return []
    return vector_store.search(embed_query(query), top_k, doc_ids)
