"""Document Q&A: retrieve relevant chunks, ask the LLM, report real sources."""

import re
from collections.abc import Iterator

from ai.llm import complete, stream_chat
from ai.prompts import NOT_FOUND_MESSAGE, RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE
from ai.rag import retrieve
from config.settings import MIN_SIMILARITY, RAG_TEMPERATURE, TOP_K


def find_relevant_chunks(
    question: str,
    doc_ids: list[str] | None = None,
    top_k: int = TOP_K,
    min_similarity: float = MIN_SIMILARITY,
) -> list[dict]:
    """Retrieve chunks and keep only those similar enough to the question."""
    hits = retrieve(question, top_k=top_k, doc_ids=doc_ids)
    return [hit for hit in hits if hit["score"] >= min_similarity]


def build_context(chunks: list[dict]) -> str:
    """Number the chunks so the AI can cite them as [1], [2], ..."""
    return "\n\n".join(
        f"[{number}] (Document: {chunk['doc_name']}, page {chunk['page']})\n{chunk['text']}"
        for number, chunk in enumerate(chunks, start=1)
    )


def build_messages(question: str, chunks: list[dict]) -> list[dict]:
    user_message = RAG_USER_TEMPLATE.format(
        context=build_context(chunks), question=question
    )
    return [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def answer_stream(question: str, chunks: list[dict]) -> Iterator[str]:
    """Stream the grounded answer."""
    return stream_chat(build_messages(question, chunks), temperature=RAG_TEMPERATURE)


def answer(question: str, chunks: list[dict]) -> str:
    """The grounded answer as one string (used by the evaluator)."""
    return complete(build_messages(question, chunks), temperature=RAG_TEMPERATURE)


def extract_sources(reply: str, chunks: list[dict]) -> tuple[list[dict], bool]:
    """Work out which real sources the answer used.

    Returns (sources, verified). verified is True when the AI cited
    specific passages; False means we fall back to all retrieved passages.
    Citation numbers that don't exist are ignored.
    """
    if NOT_FOUND_MESSAGE in reply:
        return [], True

    cited: set[int] = set()
    for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", reply):
        cited.update(int(number) for number in group.split(","))
    cited = {n for n in cited if 1 <= n <= len(chunks)}

    verified = bool(cited)
    numbers = sorted(cited) if cited else list(range(1, len(chunks) + 1))
    sources = [
        {
            "n": n,
            "doc_name": chunks[n - 1]["doc_name"],
            "page": chunks[n - 1]["page"],
            "text": chunks[n - 1]["text"],
        }
        for n in numbers
    ]
    return sources, verified
