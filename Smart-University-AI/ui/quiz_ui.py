"""Quiz page: set up, answer one question at a time, review results."""

import logging

import streamlit as st

from ai.llm import LLMError
from config.settings import QUIZ_COUNTS, QUIZ_DIFFICULTIES
from documents.loader import DocumentError, list_documents
from features.quiz import OPTION_LETTERS, generate_quiz, score_quiz
from ui.components import empty_state

logger = logging.getLogger(__name__)


def _leave_quiz() -> None:
    st.session_state.quiz = None


def _retake() -> None:
    quiz = st.session_state.quiz
    quiz.update(stage="running", current=0, answers={}, run=quiz["run"] + 1)


def _render_setup() -> None:
    documents = list_documents()
    if not documents:
        empty_state("No documents yet", "Upload a PDF in Documents first, then come back.")
        return

    by_id = {doc["doc_id"]: doc for doc in documents}
    ids = list(by_id)
    selected = st.session_state.get("selected_doc")
    doc_id = st.selectbox(
        "Document",
        ids,
        index=ids.index(selected) if selected in ids else 0,
        format_func=lambda i: by_id[i]["name"],
    )
    count = st.radio("Number of questions", QUIZ_COUNTS, horizontal=True)
    difficulty = st.radio("Difficulty", QUIZ_DIFFICULTIES, index=1, horizontal=True)

    if not st.button("Start quiz", type="primary"):
        return

    record = by_id[doc_id]
    with st.spinner("Creating your quiz from the document..."):
        try:
            questions = generate_quiz(record, count, difficulty)
        except (LLMError, DocumentError) as error:
            st.error(str(error))
            return
        except Exception:  # unexpected: log it, show a clean message
            logger.exception("Quiz generation failed")
            st.error("Something went wrong while creating the quiz. Please try again.")
            return

    st.session_state.quiz = {
        "stage": "running",
        "doc_name": record["name"],
        "difficulty": difficulty,
        "requested": count,
        "questions": questions,
        "answers": {},
        "current": 0,
        "run": 0,
    }
    st.rerun()


def _render_question(quiz: dict) -> None:
    questions = quiz["questions"]
    total = len(questions)
    index = quiz["current"]
    question = questions[index]

    if index == 0 and len(questions) < quiz["requested"]:
        st.info(
            f"The AI created {len(questions)} valid questions "
            f"(you asked for {quiz['requested']})."
        )

    st.progress(index / total, text=f"Question {index + 1} of {total} · {quiz['difficulty']}")
    st.markdown(f"### {question['question']}")

    labels = [f"{OPTION_LETTERS[n]}. {text}" for n, text in enumerate(question["options"])]
    choice = st.radio(
        "Choose one answer",
        labels,
        index=None,
        key=f"quiz_{quiz['run']}_{index}",
        label_visibility="collapsed",
    )

    is_last = index == total - 1
    next_col, cancel_col = st.columns([1, 1])
    with next_col:
        if st.button(
            "Finish quiz" if is_last else "Next question",
            type="primary",
            disabled=choice is None,
        ):
            quiz["answers"][index] = labels.index(choice)
            if is_last:
                quiz["stage"] = "results"
            else:
                quiz["current"] += 1
            st.rerun()
    with cancel_col:
        st.button("Cancel quiz", on_click=_leave_quiz)


def _render_results(quiz: dict) -> None:
    questions = quiz["questions"]
    answers = quiz["answers"]
    result = score_quiz(questions, answers)

    st.caption(f"{quiz['doc_name']} · {quiz['difficulty']}")
    score_col, percent_col = st.columns(2)
    score_col.metric("Score", f"{result['correct']} / {result['total']}")
    percent_col.metric("Percentage", f"{result['percent']}%")

    if result["percent"] >= 80:
        st.success("Excellent work! You know this material well.")
    elif result["percent"] >= 50:
        st.info("Good effort. Review the explanations below to close the gaps.")
    else:
        st.warning("Keep practising. Read the explanations and try the quiz again.")

    st.markdown("<div class='section-title'>Review</div>", unsafe_allow_html=True)
    only_wrong = st.toggle("Show only wrong answers")

    shown = 0
    for i, question in enumerate(questions):
        chosen = answers.get(i)
        is_correct = chosen == question["answer"]
        if only_wrong and is_correct:
            continue
        shown += 1

        with st.expander(
            f"{'✅' if is_correct else '❌'} Q{i + 1}. {question['question']}",
            expanded=not is_correct,
        ):
            lines = []
            for n, text in enumerate(question["options"]):
                line = f"{OPTION_LETTERS[n]}. {text}"
                if n == question["answer"]:
                    line = f"**{line}** ✓ correct answer"
                elif n == chosen:
                    line += " ✗ your answer"
                lines.append(f"- {line}")
            st.markdown("\n".join(lines))
            st.info(f"**Explanation:** {question['explanation']}")
            if question["page"]:
                st.caption(f"Based on {quiz['doc_name']}, page {question['page']}")

    if only_wrong and shown == 0:
        st.success("No wrong answers. Perfect score!")

    retake_col, new_col = st.columns(2)
    retake_col.button("Retake this quiz", on_click=_retake)
    new_col.button("New quiz", on_click=_leave_quiz)


def render_quiz() -> None:
    st.markdown("## Quiz")
    quiz = st.session_state.get("quiz")
    if quiz is None:
        _render_setup()
    elif quiz["stage"] == "running":
        _render_question(quiz)
    else:
        _render_results(quiz)
