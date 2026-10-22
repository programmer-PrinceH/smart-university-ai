import json
import random

import pytest

from ai.llm import LLMError
from features.quiz import (
    _clean_question,
    _parse,
    generate_quiz,
    score_quiz,
    select_passages,
)


def item(n=0, answer=0, page=1):
    return {
        "question": f"Question {n}?",
        "options": [f"right {n}", f"wrong a{n}", f"wrong b{n}", f"wrong c{n}"],
        "answer": answer,
        "explanation": "Because.",
        "page": page,
    }


def record(pages=3, text="Normalization reduces redundancy in tables. " * 12):
    return {
        "doc_id": "d1",
        "name": "Notes.pdf",
        "pages": [{"page": p, "text": text} for p in range(1, pages + 1)],
    }


def test_parse_handles_fences_and_extra_text():
    payload = json.dumps([item(1)])
    assert len(_parse(f"```json\n{payload}\n```")) == 1
    assert len(_parse(f"Here is your quiz:\n{payload}\nEnjoy!")) == 1


def test_parse_rejects_non_json():
    with pytest.raises(ValueError):
        _parse("Sorry, I cannot do that.")
    with pytest.raises(json.JSONDecodeError):
        _parse("[ not json ]")


def test_valid_question_is_kept_and_correct_answer_survives_shuffle():
    for seed in range(20):
        q = _clean_question(item(1, answer=2), {1}, random.Random(seed))
        assert q["options"][q["answer"]] == "wrong b1"  # the original option 2 stays correct


def test_answer_letters_and_prefixes_are_normalised():
    raw = item(1)
    raw["options"] = ["A. right", "B. wrong one", "C. wrong two", "D. wrong three"]
    raw["answer"] = "A"
    q = _clean_question(raw, {1}, random.Random(0))
    assert q["options"][q["answer"]] == "right"
    assert not any(o.startswith(("A.", "B.", "C.", "D.")) for o in q["options"])


@pytest.mark.parametrize(
    "change",
    [
        {"question": ""},
        {"options": ["a", "b", "c"]},
        {"options": ["same", "same", "x", "y"]},
        {"options": ["a", "", "c", "d"]},
        {"answer": 4},
        {"answer": -1},
        {"answer": "banana"},
        {"answer": True},
        {"answer": None},
    ],
)
def test_invalid_questions_are_rejected(change):
    raw = {**item(1), **change}
    assert _clean_question(raw, {1}, random.Random(0)) is None
    assert _clean_question("not a dict", {1}, random.Random(0)) is None


def test_page_must_be_one_we_actually_sent():
    assert _clean_question(item(1, page=1), {1, 2}, random.Random(0))["page"] == 1
    assert _clean_question(item(1, page=99), {1, 2}, random.Random(0))["page"] is None
    assert _clean_question(item(1, page="2"), {1, 2}, random.Random(0))["page"] == 2


def test_generate_quiz_returns_requested_count(fake_llm):
    fake_llm.handler = lambda m, **k: json.dumps([item(i) for i in range(8)])
    questions = generate_quiz(record(), 5, "Easy", random.Random(1))
    assert len(questions) == 5
    assert len({q["question"] for q in questions}) == 5


def test_difficulty_reaches_the_prompt(fake_llm):
    fake_llm.handler = lambda m, **k: json.dumps([item(i) for i in range(5)])
    generate_quiz(record(), 5, "Hard")
    assert "analysis" in fake_llm.calls[0]["messages"][0]["content"].lower()


def test_generate_quiz_retries_after_broken_json(fake_llm):
    replies = iter(["totally broken", json.dumps([item(i) for i in range(5)])])
    fake_llm.handler = lambda m, **k: next(replies)
    assert len(generate_quiz(record(), 5, "Medium")) == 5
    assert len(fake_llm.calls) == 2


def test_generate_quiz_combines_attempts_without_duplicates(fake_llm):
    replies = iter([json.dumps([item(0), item(1)]), json.dumps([item(1), item(2), item(3)])])
    fake_llm.handler = lambda m, **k: next(replies)
    questions = generate_quiz(record(), 5, "Medium")
    assert len(questions) == 4  # 0,1,2,3: the repeated question 1 was dropped


def test_generate_quiz_fails_cleanly_when_nothing_is_valid(fake_llm):
    fake_llm.handler = lambda m, **k: "no json here"
    with pytest.raises(LLMError):
        generate_quiz(record(), 5, "Medium")


def test_long_documents_are_sampled_across_all_pages():
    big = record(pages=60, text="Sentence about databases and keys. " * 30)
    passages, pages = select_passages(big, budget=6000)
    assert len(passages) <= 8000
    assert min(pages) == 1 and max(pages) == 60  # questions can come from the whole document
    assert len(pages) < 60


def test_short_documents_are_sent_whole():
    _, pages = select_passages(record(pages=2), budget=50000)
    assert pages == {1, 2}


def test_score_quiz():
    questions = [{"answer": 0}, {"answer": 1}, {"answer": 2}, {"answer": 3}]
    result = score_quiz(questions, {0: 0, 1: 1, 2: 0})  # one unanswered, one wrong
    assert result == {"correct": 2, "total": 4, "percent": 50}
    assert score_quiz([], {})["percent"] == 0
