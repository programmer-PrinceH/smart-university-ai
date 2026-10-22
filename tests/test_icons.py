"""Icons: every icon is valid, used icons exist, and no emoji icons are left."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from config.settings import FEATURES, NAV_ITEMS
from tests.test_app import PAGES, all_text, start
from ui.icons import BUTTON_ICONS, ICONS, icon, icon_css, svg_markup

ROOT = Path(__file__).resolve().parent.parent

# Emoji, pictographs, dingbats (check/cross marks), and a few arrow/box symbols
EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\uFF0B\u2713\u2717]"
)
ALLOWED = {"\U0001F44B"}  # the waving hand in "Hello, Prince" is kept on purpose


def emoji_in(text: str) -> set[str]:
    return {c for c in EMOJI.findall(text)} - ALLOWED


@pytest.mark.parametrize("name", list(ICONS))
def test_every_icon_is_valid_svg(name):
    root = ET.fromstring(svg_markup(name))
    assert root.tag.endswith("svg") and root.attrib["viewBox"] == "0 0 24 24"
    assert len(list(root)) >= 1


def test_icons_used_by_the_app_exist():
    names = {i["icon"] for i in NAV_ITEMS} | {f["icon"] for f in FEATURES}
    names |= {name for _, name, _ in BUTTON_ICONS}
    assert names <= set(ICONS)
    with pytest.raises(KeyError):
        icon("does-not-exist")


def test_css_defines_each_icon_and_the_avatar_styles():
    css = icon_css()
    for name in ICONS:
        assert f".ico-{name} " in css
    assert "stChatMessageAvatarUser" in css and "stChatMessageAvatarAssistant" in css
    assert css.count("data:image/svg+xml") >= len(ICONS)


def test_no_emoji_in_source_files():
    sources = [ROOT / "app.py", ROOT / "config" / "settings.py", *(ROOT / "ui").glob("*.py")]
    found = {p.name: emoji_in(p.read_text(encoding="utf-8")) for p in sources}
    assert {k: v for k, v in found.items() if v} == {}


@pytest.mark.parametrize("page", PAGES)
def test_no_emoji_on_any_rendered_page(storage, page):
    assert emoji_in(all_text(start(page))) == set()


def test_no_emoji_with_documents_chat_and_quiz_on_screen(db_doc, fake_llm):
    import json

    fake_llm.handler = lambda m, **k: "Normalization reduces data redundancy [1]."
    at = start("Documents")
    assert emoji_in(all_text(at)) == set() and "Ready" in all_text(at)

    fake_llm.handler = lambda m, **k: json.dumps([
        {"question": f"Q{i}?", "options": [f"a{i}", f"b{i}", f"c{i}", f"d{i}"],
         "answer": 0, "explanation": "e", "page": 1} for i in range(5)])
    at = start("Quiz")
    next(b for b in at.button if b.label == "Start quiz").click().run()
    quiz = at.session_state["quiz"]
    for i in range(5):
        radio = at.radio(key=f"quiz_0_{i}")
        radio.set_value(radio.options[1]).run()  # wrong answers, so every review row opens
        label = "Finish quiz" if i == 4 else "Next question"
        next(b for b in at.button if b.label == label).click().run()
    assert emoji_in(all_text(at)) == set()
    assert any("Wrong" in e.label for e in at.expander)
