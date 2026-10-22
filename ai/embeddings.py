"""Turning text into vectors (embeddings) with a local model."""

from functools import lru_cache

from config.settings import EMBEDDING_MODEL


class EmbeddingError(Exception):
    """An embedding problem with a message that is safe to show to the user."""


@lru_cache(maxsize=1)
def get_model():
    """Load the embedding model once and keep it in memory."""
    try:
        # Imported here so the app starts fast; the library is heavy.
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(EMBEDDING_MODEL)
    except Exception as error:
        raise EmbeddingError(
            "The embedding model could not be loaded. The first run needs an "
            "internet connection to download it."
        ) from error


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed many texts. Vectors are normalised (length 1) so similarity is cosine."""
    if not texts:
        return []
    model = get_model()
    try:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception as error:
        raise EmbeddingError("The text could not be converted for search.") from error
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    """Embed one question."""
    return embed_texts([text])[0]
