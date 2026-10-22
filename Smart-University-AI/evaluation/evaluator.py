"""Evaluation of Smart University AI: RAG, general LLM answers and quizzes.

Run from the project root with the venv active:

    python -m evaluation.evaluator --doc "part of your PDF file name"

Every number comes from REAL calls to the retriever and the LLM. Nothing is
simulated, so a run needs your .env key, internet, and an uploaded PDF.
Results are saved to evaluation/results/ as JSON and Markdown.
"""

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from ai import vector_store
from ai.embeddings import EmbeddingError
from ai.llm import LLMError, complete
from ai.prompts import NOT_FOUND_MESSAGE
from ai.rag import index_document, retrieve
from ai.vector_store import VectorStoreError
from config import settings
from documents.loader import DocumentError, list_documents
from features.chat import build_messages as build_chat_messages
from features.document_qa import answer, extract_sources
from features.quiz import generate_quiz

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_QUESTIONS = EVAL_DIR / "test_questions.json"
RESULTS_DIR = EVAL_DIR / "results"

CORRECT_THRESHOLD = 0.5  # an answer is "correct" if it has at least half the keywords
UNCERTAINTY_PHRASES = [
    "does not exist", "doesn't exist", "not a real", "no such", "not aware",
    "isn't a", "is not a", "cannot find", "can't find", "couldn't find",
    "not sure", "unable to verify", "don't have information", "do not have information",
    "no record", "not familiar", "fictional", "i could not find", "no built-in",
]


# ----------------------------------------------------------- scoring helpers
def keyword_score(text: str, keywords: list[str]) -> float | None:
    """Fraction of expected keywords found in the text (case-insensitive).

    A keyword may list alternatives separated by '|', e.g. "generalise|generalize".
    This is a transparent PROXY for correctness; read the saved answers too.
    """
    if not keywords:
        return None
    lowered = text.lower()
    found = sum(
        1
        for keyword in keywords
        if any(option.strip().lower() in lowered for option in keyword.split("|"))
    )
    return found / len(keywords)


def contains_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _rate(values: list[float]) -> float | None:
    """Average of 0/1 or numeric values, or None when there is nothing to average."""
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def is_placeholder(item: dict) -> bool:
    return str(item.get("question", "")).strip().upper().startswith("TODO")


# ---------------------------------------------------------------------- RAG
def evaluate_rag(
    record: dict, items: list[dict], top_k: int, min_similarity: float, delay: float = 0.0
) -> list[dict]:
    """Ask each test question through the real pipeline and record the evidence."""
    rows: list[dict] = []
    for item in items:
        question = item["question"]
        expected_pages = item.get("expected_pages") or []
        row = {
            "id": item.get("id", ""),
            "type": item.get("type", "in_document"),
            "question": question,
            "expected_pages": expected_pages,
        }
        started = time.perf_counter()
        try:
            retrieved = retrieve(question, top_k=top_k, doc_ids=[record["doc_id"]])
            chunks = [hit for hit in retrieved if hit["score"] >= min_similarity]
            reply = answer(question, chunks) if chunks else NOT_FOUND_MESSAGE
        except (LLMError, EmbeddingError, VectorStoreError) as error:
            row["error"] = str(error)
            rows.append(row)
            continue
        row["seconds"] = round(time.perf_counter() - started, 2)

        sources, verified = extract_sources(reply, chunks) if chunks else ([], True)
        retrieved_pages = [hit["page"] for hit in retrieved]
        refused = NOT_FOUND_MESSAGE in reply
        row.update(
            answer=reply,
            refused=refused,
            retrieved_pages=retrieved_pages,
            top_scores=[round(hit["score"], 3) for hit in retrieved],
            cited_pages=sorted({s["page"] for s in sources}),
            citations_verified=verified and bool(sources),
        )

        if row["type"] == "out_of_document":
            row["hallucinated"] = not refused
        else:
            if expected_pages:
                ranks = [i + 1 for i, p in enumerate(retrieved_pages) if p in expected_pages]
                row["retrieval_hit"] = bool(ranks)
                row["retrieval_rank"] = ranks[0] if ranks else None
                row["citation_correct"] = bool(
                    row["citations_verified"] and set(row["cited_pages"]) & set(expected_pages)
                )
            score = keyword_score(reply, item.get("expected_keywords", []))
            row["keyword_score"] = None if score is None else round(score, 2)
            row["correct"] = None if score is None else (
                score >= CORRECT_THRESHOLD and not refused
            )
            row["grounded"] = row["citations_verified"] and not refused
            row["wrongly_refused"] = refused
        rows.append(row)
        if delay:
            time.sleep(delay)
    return rows


def summarize_rag(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    inside = [r for r in ok if r["type"] != "out_of_document"]
    outside = [r for r in ok if r["type"] == "out_of_document"]
    with_pages = [r for r in inside if r.get("expected_pages")]
    return {
        "questions_in_document": len(inside),
        "questions_out_of_document": len(outside),
        "errors": len(rows) - len(ok),
        "retrieval_hit_rate": _rate([r["retrieval_hit"] for r in with_pages]),
        "mean_reciprocal_rank": _rate(
            [1 / r["retrieval_rank"] if r["retrieval_rank"] else 0 for r in with_pages]
        ),
        "answer_correct_rate": _rate([r["correct"] for r in inside]),
        "mean_keyword_score": _rate([r["keyword_score"] for r in inside]),
        "grounding_rate": _rate([r["grounded"] for r in inside]),
        "citation_accuracy": _rate([r["citation_correct"] for r in with_pages]),
        "wrongly_refused_rate": _rate([r["wrongly_refused"] for r in inside]),
        "refusal_accuracy_out_of_document": _rate([r["refused"] for r in outside]),
        "hallucination_rate_out_of_document": _rate([r["hallucinated"] for r in outside]),
        "avg_seconds": _rate([r["seconds"] for r in ok]),
    }


# ----------------------------------------------------------- general LLM answers
def evaluate_chat(items: list[dict], delay: float = 0.0) -> list[dict]:
    rows: list[dict] = []
    for item in items:
        question = item["question"]
        kind = item.get("type", "knowledge")
        row = {"id": item.get("id", ""), "type": kind, "question": question}
        started = time.perf_counter()
        try:
            reply = complete(
                build_chat_messages([{"role": "user", "content": question}]),
                settings.LLM_TEMPERATURE,
                settings.LLM_MAX_TOKENS,
            )
        except LLMError as error:
            row["error"] = str(error)
            rows.append(row)
            continue
        row["seconds"] = round(time.perf_counter() - started, 2)
        row["answer"] = reply
        if kind == "false_premise":
            row["admitted_uncertainty"] = contains_any(reply, UNCERTAINTY_PHRASES)
            row["hallucinated"] = not row["admitted_uncertainty"]
        else:
            score = keyword_score(reply, item.get("expected_keywords", []))
            row["keyword_score"] = None if score is None else round(score, 2)
            row["correct"] = None if score is None else score >= CORRECT_THRESHOLD
        rows.append(row)
        if delay:
            time.sleep(delay)
    return rows


def summarize_chat(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    knowledge = [r for r in ok if r["type"] != "false_premise"]
    traps = [r for r in ok if r["type"] == "false_premise"]
    return {
        "knowledge_questions": len(knowledge),
        "false_premise_questions": len(traps),
        "errors": len(rows) - len(ok),
        "correct_rate": _rate([r["correct"] for r in knowledge]),
        "mean_keyword_score": _rate([r["keyword_score"] for r in knowledge]),
        "hallucination_rate_false_premise": _rate([r["hallucinated"] for r in traps]),
        "avg_seconds": _rate([r["seconds"] for r in ok]),
    }


# ----------------------------------------------------------------------- quiz
def evaluate_quiz(record: dict, count: int, difficulty: str) -> dict:
    started = time.perf_counter()
    try:
        questions = generate_quiz(record, count, difficulty)
    except (LLMError, DocumentError) as error:
        return {"error": str(error), "requested": count, "difficulty": difficulty}
    seconds = round(time.perf_counter() - started, 2)

    positions = [q["answer"] for q in questions]
    return {
        "requested": count,
        "difficulty": difficulty,
        "valid_questions": len(questions),
        "validity_rate": round(len(questions) / count, 3),
        "page_grounded_rate": _rate([q["page"] is not None for q in questions]),
        "answer_position_counts": {
            letter: positions.count(i) for i, letter in enumerate("ABCD")
        },
        "seconds": seconds,
        # Answer-key accuracy needs a human: open the PDF, check each question and
        # set manual_correct to true/false in the saved JSON (then count them).
        "questions": [
            {
                "question": q["question"],
                "options": q["options"],
                "answer": "ABCD"[q["answer"]],
                "page": q["page"],
                "manual_correct": None,
            }
            for q in questions
        ],
    }


# -------------------------------------------------------------------- reports
def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _table(title: str, metrics: dict) -> list[str]:
    lines = [f"### {title}", "", "| Metric | Value |", "|---|---|"]
    lines += [f"| {name.replace('_', ' ')} | {_fmt(value)} |" for name, value in metrics.items()]
    return lines + [""]


def build_markdown(results: dict) -> str:
    cfg = results["config"]
    lines = [
        f"# Evaluation report: {results['label']}",
        "",
        f"- Date: {results['created_at']}",
        f"- Document: {results['document']}",
        f"- Model: {cfg['model']}",
        f"- top-k: {cfg['top_k']} · min similarity: {cfg['min_similarity']} · "
        f"chunk size: {cfg['chunk_size']} · overlap: {cfg['chunk_overlap']}",
        f"- Temperatures: chat {cfg['llm_temperature']} · RAG {cfg['rag_temperature']} · "
        f"quiz {cfg['quiz_temperature']}",
        "",
    ]
    if "rag" in results:
        lines += _table("RAG (Document Q&A)", results["rag"]["summary"])
    if "chat" in results:
        lines += _table("General LLM answers (AI Chat)", results["chat"]["summary"])
    if "quiz" in results:
        quiz = {k: v for k, v in results["quiz"].items() if k != "questions"}
        lines += _table("Quiz generation", quiz)
    lines += [
        "Notes: correctness is a keyword-based proxy (see evaluator.py); read the saved "
        "answers in the JSON file to confirm. Quiz answer-key accuracy must be checked "
        "by hand (manual_correct fields).",
        "",
    ]
    return "\n".join(lines)


def save_results(results: dict) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"eval_{stamp}.json"
    md_path = RESULTS_DIR / f"eval_{stamp}.md"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(build_markdown(results), encoding="utf-8")
    return json_path, md_path


# ----------------------------------------------------------------------- main
def find_document(name_part: str) -> dict | None:
    for record in list_documents():
        if name_part.lower() in record["name"].lower():
            return record
    return None


def run_evaluation(args: argparse.Namespace) -> dict:
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    record = find_document(args.doc)
    if record is None:
        raise SystemExit(f"No uploaded document matches '{args.doc}'. Upload it in the app first.")

    if vector_store.count_chunks(record["doc_id"]) == 0:
        print("Indexing the document first...")
        index_document(record)

    results = {
        "label": args.label,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "document": record["name"],
        "config": {
            "model": settings.LLM_MODEL,
            "top_k": args.top_k,
            "min_similarity": args.min_similarity,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "embedding_model": settings.EMBEDDING_MODEL,
            "llm_temperature": settings.LLM_TEMPERATURE,
            "rag_temperature": settings.RAG_TEMPERATURE,
            "quiz_temperature": settings.QUIZ_TEMPERATURE,
        },
    }

    if not args.skip_rag:
        items = [i for i in questions.get("rag", []) if not is_placeholder(i)]
        skipped = len(questions.get("rag", [])) - len(items)
        if skipped:
            print(f"Skipping {skipped} RAG question(s) that still say TODO in the questions file.")
        print(f"Evaluating RAG on {len(items)} question(s)...")
        rows = evaluate_rag(record, items, args.top_k, args.min_similarity, args.delay)
        results["rag"] = {"summary": summarize_rag(rows), "rows": rows}

    if not args.skip_chat:
        items = [i for i in questions.get("chat", []) if not is_placeholder(i)]
        print(f"Evaluating AI Chat on {len(items)} question(s)...")
        rows = evaluate_chat(items, args.delay)
        results["chat"] = {"summary": summarize_chat(rows), "rows": rows}

    if not args.skip_quiz:
        quiz_cfg = questions.get("quiz", {})
        count = args.quiz_count or quiz_cfg.get("count", 5)
        difficulty = args.quiz_difficulty or quiz_cfg.get("difficulty", "Medium")
        print(f"Evaluating quiz generation ({count} questions, {difficulty})...")
        results["quiz"] = evaluate_quiz(record, count, difficulty)
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Smart University AI.")
    parser.add_argument("--doc", required=True, help="part of the uploaded PDF's file name")
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--label", default="baseline", help="a name for this run")
    parser.add_argument("--top-k", type=int, default=settings.TOP_K)
    parser.add_argument("--min-similarity", type=float, default=settings.MIN_SIMILARITY)
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    parser.add_argument("--skip-rag", action="store_true")
    parser.add_argument("--skip-chat", action="store_true")
    parser.add_argument("--skip-quiz", action="store_true")
    parser.add_argument("--quiz-count", type=int, default=0)
    parser.add_argument("--quiz-difficulty", choices=settings.QUIZ_DIFFICULTIES, default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = run_evaluation(args)
    json_path, md_path = save_results(results)
    print()
    print(build_markdown(results))
    print(f"Saved: {json_path}\nSaved: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
