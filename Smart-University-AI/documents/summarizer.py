"""PDF summarizer: one call for short documents, map-reduce for long ones."""

import json
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ai.llm import LLMError, complete
from ai.prompts import (
    CONDENSE_SYSTEM_PROMPT,
    SECTION_NOTES_SYSTEM_PROMPT,
    SECTION_USER_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_TEMPLATE,
)
from config.settings import (
    LLM_MODEL,
    NOTES_MAX_TOKENS,
    SUMMARIES_DIR,
    SUMMARY_MAX_TOKENS,
    SUMMARY_SECTION_CHARS,
    SUMMARY_TEMPERATURE,
)
from documents.loader import DocumentError

MAX_CONDENSE_ROUNDS = 3
Progress = Callable[[float, str], None]  # (fraction 0-1, message)


def build_sections(record: dict, max_chars: int | None = None) -> list[dict]:
    """Group whole pages into sections of at most ~max_chars characters."""
    max_chars = max_chars or SUMMARY_SECTION_CHARS
    sections: list[dict] = []
    blocks: list[str] = []
    length = 0
    first = last = 0
    for page in record["pages"]:
        if not page["text"]:
            continue
        block = f"--- Page {page['page']} ---\n{page['text']}"
        if blocks and length + len(block) > max_chars:
            sections.append({"start": first, "end": last, "text": "\n\n".join(blocks)})
            blocks, length = [], 0
        if not blocks:
            first = page["page"]
        blocks.append(block)
        length += len(block)
        last = page["page"]
    if blocks:
        sections.append({"start": first, "end": last, "text": "\n\n".join(blocks)})
    return sections


def _batch(texts: list[str], max_chars: int) -> list[list[str]]:
    """Group texts into batches that each fit within max_chars."""
    batches: list[list[str]] = []
    current: list[str] = []
    length = 0
    for text in texts:
        if current and length + len(text) > max_chars:
            batches.append(current)
            current, length = [], 0
        current.append(text)
        length += len(text)
    if current:
        batches.append(current)
    return batches


def _condense(notes: list[str], report: Progress) -> str:
    """Merge section notes until they are short enough for the final summary."""
    for round_number in range(1, MAX_CONDENSE_ROUNDS + 1):
        if len("\n\n".join(notes)) <= SUMMARY_SECTION_CHARS:
            break
        report(0.85, f"Combining notes (round {round_number})...")
        notes = [
            complete(
                [
                    {"role": "system", "content": CONDENSE_SYSTEM_PROMPT},
                    {"role": "user", "content": "\n\n".join(batch)},
                ],
                SUMMARY_TEMPERATURE,
                NOTES_MAX_TOKENS,
            )
            for batch in _batch(notes, SUMMARY_SECTION_CHARS)
        ]
    return "\n\n".join(notes)


def summarize_document(record: dict, progress: Progress | None = None) -> dict:
    """Summarise a stored document, save the result and return it."""
    report: Progress = progress or (lambda fraction, message: None)
    started = time.perf_counter()

    sections = build_sections(record)
    if not sections:
        raise DocumentError("This document has no text to summarise.")

    if len(sections) == 1:
        content, method = sections[0]["text"], "direct"
    else:
        notes: list[str] = []
        for number, section in enumerate(sections, start=1):
            report(
                0.05 + 0.75 * (number - 1) / len(sections),
                f"Reading section {number} of {len(sections)} "
                f"(pages {section['start']}-{section['end']})...",
            )
            user_message = SECTION_USER_TEMPLATE.format(
                number=number,
                total=len(sections),
                start=section["start"],
                end=section["end"],
                text=section["text"],
            )
            reply = complete(
                [
                    {"role": "system", "content": SECTION_NOTES_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                SUMMARY_TEMPERATURE,
                NOTES_MAX_TOKENS,
            )
            notes.append(f"### Pages {section['start']}-{section['end']}\n{reply}")
        content, method = _condense(notes, report), "map-reduce"

    report(0.9, "Writing the final summary...")
    summary = complete(
        [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": SUMMARY_USER_TEMPLATE.format(name=record["name"], content=content),
            },
        ],
        SUMMARY_TEMPERATURE,
        SUMMARY_MAX_TOKENS,
    )
    if not summary:
        raise LLMError("The AI returned an empty summary. Please try again.")

    result = {
        "doc_id": record["doc_id"],
        "summary": summary,
        "method": method,
        "sections": len(sections),
        "model": LLM_MODEL,
        "seconds": round(time.perf_counter() - started, 1),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save(result)
    report(1.0, "Done")
    return result


def _path(doc_id: str) -> Path:
    return SUMMARIES_DIR / f"{doc_id}.json"


def _save(result: dict) -> None:
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    _path(result["doc_id"]).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


def load_summary(doc_id: str) -> dict | None:
    """The saved summary of a document, or None if there isn't one."""
    path = _path(doc_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
