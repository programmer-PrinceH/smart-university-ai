"""Splitting page text into overlapping chunks that keep their page number."""

import re

from config.settings import CHUNK_OVERLAP, CHUNK_SIZE, MIN_CHUNK_CHARS


def _split_units(text: str, max_len: int) -> list[str]:
    """Break text into sentences/lines; hard-split any piece that is too long."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    units: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_len:
            units.append(part)
        else:
            units.extend(part[i : i + max_len] for i in range(0, len(part), max_len))
    return units


def _overlap_tail(units: list[str], overlap: int) -> tuple[list[str], int]:
    """The last few units of a finished chunk, reused at the start of the next one."""
    tail: list[str] = []
    length = 0
    for unit in reversed(units):
        added = len(unit) + (1 if tail else 0)
        if length + added > overlap:
            break
        tail.insert(0, unit)
        length += added
    return tail, length


def split_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Pack sentences into chunks of at most ~chunk_size characters, with overlap."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for unit in _split_units(text, chunk_size - overlap):
        added = len(unit) + (1 if current else 0)
        if current and length + added > chunk_size:
            chunks.append(" ".join(current))
            current, length = _overlap_tail(current, overlap)
            added = len(unit) + (1 if current else 0)
        current.append(unit)
        length += added
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_document(record: dict) -> list[dict]:
    """Chunk every page of a stored document. Chunks never cross page borders."""
    chunks: list[dict] = []
    for page in record["pages"]:
        for index, piece in enumerate(split_text(page["text"])):
            if len(piece) < MIN_CHUNK_CHARS:
                continue
            chunks.append(
                {
                    "chunk_id": f"{record['doc_id']}_p{page['page']}_c{index}",
                    "doc_id": record["doc_id"],
                    "doc_name": record["name"],
                    "page": page["page"],
                    "chunk_index": index,
                    "text": piece,
                }
            )
    return chunks
