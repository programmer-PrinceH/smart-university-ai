"""UI smoke tests: run the real Streamlit app with a fake LLM and fake embeddings."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import database.database as db

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PAGES = ["Home", "Chat", "Documents", "Quiz", "Python Assistant"]


def start(page: str = "Home") -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["page"] = page
    return at.run()


def all_text(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [e.value for e in at.error]
    parts += [w.value for w in at.warning] + [i.value for i in at.info]
    parts += [c.value for c in at.caption] + [s.value for s in at.success]
    return "\n".join(str(p) for p in parts)


def test_home_screen(storage):
    at = start()
    assert not at.exception
    text = all_text(at)
    assert "Hello, Prince" in text and "How can I help you today?" in text
    for title in ["AI Chat", "Ask My Documents", "Summarize PDF", "Generate Quiz", "Python Assistant"]:
        assert title in text
    assert "No documents yet" in text


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_errors(storage, page):
    assert not start(page).exception


def test_sidebar_navigation(storage):
    at = start()
    at.sidebar.button(key="nav_quiz").click().run()
    assert at.session_state["page"] == "Quiz" and not at.exception
    at.sidebar.button(key="nav_python").click().run()
    assert at.session_state["page"] == "Python Assistant" and not at.exception


def test_feature_cards_open_the_right_views(storage):
    at = start()
    at.button(key="open_ask_docs").click().run()
    assert at.session_state["page"] == "Documents" and at.session_state["doc_mode"] == "Ask"
    at = start()
    at.button(key="open_summarize").click().run()
    assert at.session_state["doc_mode"] == "Summarize"


def test_dark_mode_changes_the_theme(storage):
    at = start()
    assert "#F7F8FC" in all_text(at)
    at.sidebar.toggle(key="dark_mode").set_value(True).run()
    assert "#0F1117" in all_text(at) and not at.exception


def test_chat_remembers_context_and_saves_the_conversation(storage, fake_llm):
    fake_llm.handler = lambda m, **k: "Python is a programming language."
    at = start("Chat")
    at.chat_input[0].set_value("What is Python?").run()
    assert not at.exception
    assert [m.name for m in at.chat_message] == ["user", "assistant"]
    assert "programming language" in at.chat_message[1].markdown[0].value

    at.chat_input[0].set_value("What are its advantages?").run()
    sent = fake_llm.calls[-1]["messages"]
    assert [m["role"] for m in sent] == ["system", "user", "assistant", "user"]  # memory works
    assert "What is Python?" in sent[1]["content"]

    conversations = db.list_conversations()
    assert len(conversations) == 1 and conversations[0]["title"] == "What is Python?"
    assert len(db.get_messages(conversations[0]["id"])) == 4


def test_saved_conversations_appear_in_sidebar_and_can_be_reopened(storage, fake_llm):
    fake_llm.handler = lambda m, **k: "Answer one."
    at = start("Chat")
    at.chat_input[0].set_value("Explain loops").run()
    cid = db.list_conversations()[0]["id"]
    assert any(b.key == f"convo_{cid}" for b in at.sidebar.button)

    at.sidebar.button(key="new_chat").click().run()
    assert len(at.chat_message) == 0
    at.sidebar.button(key=f"convo_{cid}").click().run()
    assert len(at.chat_message) == 2 and not at.exception

    at.sidebar.button(key=f"delc_{cid}").click().run()
    assert db.list_conversations() == [] and len(at.chat_message) == 0


def test_home_composer_starts_a_chat(storage, fake_llm):
    fake_llm.handler = lambda m, **k: "Hello student."
    at = start("Home")
    at.chat_input[0].set_value("Hi there").run()
    assert at.session_state["page"] == "Chat"
    assert [m.name for m in at.chat_message] == ["user", "assistant"]


def test_ai_errors_show_a_clean_message_not_a_traceback(storage, fake_llm):
    fake_llm.error = RuntimeError("secret internal detail")
    at = start("Chat")
    at.chat_input[0].set_value("hello").run()
    assert not at.exception
    text = all_text(at)
    assert "Something went wrong" in text and "secret internal detail" not in text
    assert "Traceback" not in text


def test_python_assistant_form_sends_code_and_error(storage, fake_llm):
    fake_llm.handler = lambda m, **k: "## What the error means\nx is not defined."
    at = start("Python Assistant")
    at.text_area(key="py_code").set_value("print(x)")
    at.text_area(key="py_error").set_value("NameError: name 'x' is not defined")
    at.button(key="py_send").click().run()
    assert not at.exception
    sent = fake_llm.calls[-1]["messages"]
    assert "print(x)" in sent[-1]["content"] and "NameError" in sent[-1]["content"]
    assert "Python Assistant" in sent[0]["content"]
    assert db.list_conversations()[0]["mode"] == "python"


def test_python_form_requires_something_to_send(storage, fake_llm):
    at = start("Python Assistant")
    at.button(key="py_send").click().run()
    assert any("Paste some code" in w.value for w in at.warning)
    assert fake_llm.calls == []


def test_documents_library_shows_ready_document(db_doc):
    at = start("Documents")
    assert not at.exception
    text = all_text(at)
    assert "Database_Notes.pdf" in text and "Ready" in text and "3 pages" in text


def test_ask_my_documents_shows_real_sources(db_doc, fake_llm):
    fake_llm.handler = lambda m, **k: "Normalization reduces data redundancy [1]."
    at = start("Documents")
    at.radio(key="doc_mode").set_value("Ask").run()
    at.chat_input[0].set_value("normalization reduces data redundancy").run()
    assert not at.exception
    text = all_text(at)
    assert "Database_Notes.pdf" in text and "Page 1" in text
    sent = fake_llm.calls[-1]["messages"]
    assert "(Document: Database_Notes.pdf, page 1)" in sent[-1]["content"]


def test_ask_my_documents_refuses_when_nothing_relevant(db_doc, fake_llm):
    at = start("Documents")
    at.radio(key="doc_mode").set_value("Ask").run()
    at.chat_input[0].set_value("zebra giraffe savanna migration").run()
    assert "could not find the answer" in all_text(at)
    assert fake_llm.calls == []  # the AI is not even called


def test_summarize_view_creates_and_shows_summary(db_doc, fake_llm):
    fake_llm.handler = lambda m, **k: "## Short overview\nA tidy summary."
    at = start("Documents")
    at.radio(key="doc_mode").set_value("Summarize").run()
    next(b for b in at.button if b.label == "Summarize document").click().run()
    assert not at.exception
    assert "A tidy summary." in all_text(at)
    assert "Direct summary" in all_text(at)


def quiz_reply():
    return json.dumps([
        {"question": f"Question {i}?", "options": [f"right{i}", f"x{i}", f"y{i}", f"z{i}"],
         "answer": 0, "explanation": f"Because {i}.", "page": 1}
        for i in range(5)
    ])


def test_quiz_flow_from_start_to_score(db_doc, fake_llm):
    fake_llm.handler = lambda m, **k: quiz_reply()
    at = start("Quiz")
    next(b for b in at.button if b.label == "Start quiz").click().run()
    assert not at.exception
    quiz = at.session_state["quiz"]
    assert quiz["stage"] == "running" and len(quiz["questions"]) == 5

    for index in range(5):
        radio = at.radio(key=f"quiz_0_{index}")
        question = at.session_state["quiz"]["questions"][index]
        correct_label = f"{'ABCD'[question['answer']]}. {question['options'][question['answer']]}"
        wrong_label = next(o for o in radio.options if o != correct_label)
        radio.set_value(correct_label if index < 4 else wrong_label).run()  # last one wrong
        label = "Finish quiz" if index == 4 else "Next question"
        next(b for b in at.button if b.label == label).click().run()

    assert at.session_state["quiz"]["stage"] == "results" and not at.exception
    values = {m.label: m.value for m in at.metric}
    assert values == {"Score": "4 / 5", "Percentage": "80%"}
