"""Quiz generator: build multiple-choice questions from a stored document."""

import json
import random
import re

from ai.llm import LLMError, complete
from ai.prompts import DIFFICULTY_GUIDES, QUIZ_SYSTEM_PROMPT, QUIZ_USER_TEMPLATE
from config.settings import QUIZ_CONTEXT_CHARS, QUIZ_MAX_TOKENS, QUIZ_TEMPERATURE
from documents.chunker import chunk_document
from documents.loader import DocumentError

OPTION_LETTERS = "ABCD"
MAX_ATTEMPTS = 2  # one retry if the AI returns broken or too few questions


def select_passages(record: dict, budget: int = QUIZ_CONTEXT_CHARS) -> tuple[str, set[int]]:
    """Choose document text for the quiz. Long documents are sampled evenly,
    so questions come from the whole document, not only the first pages."""
    chunks = chunk_document(record)
    if not chunks:
        raise DocumentError("This document has no text to build a quiz from.")

    total = sum(len(c["text"]) for c in chunks)
    picked = chunks
    if total > budget:
        count = max(1, int(budget / (total / len(chunks))))
        if count < len(chunks):
            if count == 1:
                picked = [chunks[0]]
            else:
                step = (len(chunks) - 1) / (count - 1)
                positions = sorted({round(i * step) for i in range(count)})
                picked = [chunks[p] for p in positions]

    text = "\n\n".join(f"--- Page {c['page']} ---\n{c['text']}" for c in picked)
    return text, {c["page"] for c in picked}


def _parse(reply: str) -> list:
    """Pull the JSON array out of the AI's reply (it may add fences or extra text)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", reply.strip(), flags=re.IGNORECASE)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        raise ValueError("no JSON array found")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, list):
        raise ValueError("JSON is not a list")
    return data


def _clean_question(item, valid_pages: set[int], rng: random.Random) -> dict | None:
    """Validate one question. Returns None if anything is wrong."""
    if not isinstance(item, dict):
        return None

    question = str(item.get("question", "")).strip()
    explanation = str(item.get("explanation", "")).strip()
    options = item.get("options")
    if not question or not isinstance(options, list) or len(options) != 4:
        return None

    # Remove "A. " style prefixes if the AI added them
    options = [re.sub(r"^\(?[A-Da-d][\).:]\s+", "", str(o).strip()) for o in options]
    if any(not o for o in options) or len({o.lower() for o in options}) < 4:
        return None

    answer = item.get("answer")
    if isinstance(answer, str):
        letter = answer.strip().upper()
        if letter in list(OPTION_LETTERS):
            answer = OPTION_LETTERS.index(letter)
        elif letter.isdigit():
            answer = int(letter)
    if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer <= 3:
        return None

    # Shuffle so the correct answer is not always in the same position
    correct_text = options[answer]
    rng.shuffle(options)

    page = item.get("page")
    if isinstance(page, str) and page.strip().isdigit():
        page = int(page.strip())
    if isinstance(page, bool) or page not in valid_pages:
        page = None  # only keep pages that really were in the text we sent

    return {
        "question": question,
        "options": options,
        "answer": options.index(correct_text),
        "explanation": explanation or "No explanation was provided.",
        "page": page,
    }


def generate_quiz(
    record: dict, count: int, difficulty: str, rng: random.Random | None = None
) -> list[dict]:
    """Create up to `count` validated multiple-choice questions from a document."""
    rng = rng or random.Random()
    passages, valid_pages = select_passages(record)
    messages = [
        {
            "role": "system",
            "content": QUIZ_SYSTEM_PROMPT.format(difficulty_guide=DIFFICULTY_GUIDES[difficulty]),
        },
        {
            "role": "user",
            "content": QUIZ_USER_TEMPLATE.format(
                count=count, name=record["name"], passages=passages
            ),
        },
    ]

    questions: list[dict] = []
    seen: set[str] = set()
    for _ in range(MAX_ATTEMPTS):
        reply = complete(messages, QUIZ_TEMPERATURE, QUIZ_MAX_TOKENS)
        try:
            items = _parse(reply)
        except ValueError:  # includes JSON decode errors
            continue
        for item in items:
            question = _clean_question(item, valid_pages, rng)
            if question and question["question"].lower() not in seen:
                seen.add(question["question"].lower())
                questions.append(question)
        if len(questions) >= count:
            break

    if not questions:
        raise LLMError("The quiz could not be created this time. Please try again.")
    return questions[:count]


def score_quiz(questions: list[dict], answers: dict[int, int]) -> dict:
    """Count correct answers. `answers` maps question number to the chosen option."""
    correct = sum(1 for i, q in enumerate(questions) if answers.get(i) == q["answer"])
    total = len(questions)
    return {
        "correct": correct,
        "total": total,
        "percent": round(100 * correct / total) if total else 0,
    }
