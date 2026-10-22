import json
import types

import pytest

import evaluation.evaluator as ev
from documents.processor import process_pdf
from tests.helpers import DB_PAGES, make_pdf


def test_keyword_score_with_alternatives():
    assert ev.keyword_score("Lists are mutable, tuples immutable", ["mutable", "immutable"]) == 1.0
    assert ev.keyword_score("It is generalised well", ["generali|generalis", "training"]) == 0.5
    assert ev.keyword_score("anything", []) is None
    assert ev.keyword_score("ABC", ["abc"]) == 1.0  # case-insensitive


def test_uncertainty_detection():
    assert ev.contains_any("That function does not exist in Python.", ev.UNCERTAINTY_PHRASES)
    assert not ev.contains_any("sortfast() sorts the list very fast.", ev.UNCERTAINTY_PHRASES)


def test_placeholders_are_recognised():
    assert ev.is_placeholder({"question": "TODO: write a question"})
    assert not ev.is_placeholder({"question": "What is normalization?"})


def test_rate_ignores_missing_values():
    assert ev._rate([1, 0, None, 1]) == 0.667
    assert ev._rate([]) is None


def test_summarize_rag_math():
    rows = [
        {"type": "in_document", "expected_pages": [1], "retrieval_hit": True, "retrieval_rank": 1,
         "correct": True, "keyword_score": 1.0, "grounded": True, "citation_correct": True,
         "wrongly_refused": False, "seconds": 2.0},
        {"type": "in_document", "expected_pages": [2], "retrieval_hit": True, "retrieval_rank": 2,
         "correct": False, "keyword_score": 0.0, "grounded": False, "citation_correct": False,
         "wrongly_refused": True, "seconds": 4.0},
        {"type": "out_of_document", "refused": True, "hallucinated": False, "seconds": 1.0},
        {"type": "out_of_document", "refused": False, "hallucinated": True, "seconds": 1.0},
        {"type": "in_document", "question": "x", "error": "rate limited"},
    ]
    summary = ev.summarize_rag(rows)
    assert summary["errors"] == 1
    assert summary["retrieval_hit_rate"] == 1.0
    assert summary["mean_reciprocal_rank"] == 0.75
    assert summary["answer_correct_rate"] == 0.5
    assert summary["hallucination_rate_out_of_document"] == 0.5
    assert summary["refusal_accuracy_out_of_document"] == 0.5
    assert summary["avg_seconds"] == 2.0


def quiz_json():
    return json.dumps([
        {"question": f"Q{i}?", "options": [f"a{i}", f"b{i}", f"c{i}", f"d{i}"],
         "answer": i % 4, "explanation": "e", "page": 1 + i % 3}
        for i in range(6)
    ])


def test_full_evaluation_run_with_fake_models(db_doc, fake_llm, tmp_path):
    def handler(messages, **kwargs):
        system = messages[0]["content"]
        user = messages[-1]["content"]
        if "JSON array" in system:
            return quiz_json()
        if "context passages" in system:
            return "Normalization reduces data redundancy [1]."
        if "sortfast" in user:
            return "There is no such function in Python."
        return "Lists are mutable and tuples are immutable."

    fake_llm.handler = handler
    questions = {
        "rag": [
            {"id": "R1", "type": "in_document", "question": "normalization reduces data redundancy",
             "expected_keywords": ["redundancy"], "expected_pages": [1]},
            {"id": "R2", "type": "in_document", "question": "TODO: skipped placeholder"},
            {"id": "O1", "type": "out_of_document", "question": "zebra giraffe savanna?"},
        ],
        "chat": [
            {"id": "C1", "type": "knowledge", "question": "list vs tuple?",
             "expected_keywords": ["mutable", "immutable"]},
            {"id": "C2", "type": "false_premise", "question": "Explain list.sortfast()."},
        ],
        "quiz": {"count": 5, "difficulty": "Easy"},
    }
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(questions), encoding="utf-8")

    args = ev.parse_args(["--doc", "database_notes", "--questions", str(path),
                          "--delay", "0", "--label", "unit-test", "--min-similarity", "0.2"])
    results = ev.run_evaluation(args)

    rag = results["rag"]["summary"]
    assert rag["questions_in_document"] == 1 and rag["questions_out_of_document"] == 1
    assert rag["retrieval_hit_rate"] == 1.0
    assert rag["answer_correct_rate"] == 1.0
    assert rag["grounding_rate"] == 1.0
    assert rag["citation_accuracy"] == 1.0
    assert rag["hallucination_rate_out_of_document"] == 0.0  # off-topic question was refused

    chat = results["chat"]["summary"]
    assert chat["correct_rate"] == 1.0
    assert chat["hallucination_rate_false_premise"] == 0.0

    quiz = results["quiz"]
    assert quiz["valid_questions"] == 5 and quiz["validity_rate"] == 1.0
    assert all(q["manual_correct"] is None for q in quiz["questions"])  # humans must check

    json_path, md_path = ev.save_results(results)
    assert json_path.exists() and "Evaluation report: unit-test" in md_path.read_text()


def test_errors_are_recorded_not_crashing(db_doc, fake_llm):
    from ai.llm import LLMError

    fake_llm.error = RuntimeError("down")
    rows = ev.evaluate_chat([{"id": "C1", "question": "hi", "expected_keywords": ["x"]}])
    assert "error" in rows[0]
    assert ev.summarize_chat(rows)["errors"] == 1


def test_unknown_document_stops_with_a_clear_message(storage):
    args = ev.parse_args(["--doc", "nothing-matches"])
    with pytest.raises(SystemExit, match="No uploaded document"):
        ev.run_evaluation(args)
