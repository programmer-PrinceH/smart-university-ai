"""Professional line icons (24x24, outline style) drawn as CSS masks.

Each icon is an SVG shape used as a CSS mask on an element whose background is
the current text colour. So icons automatically follow the theme: light mode,
dark mode, hover and active states, with no icon font and no image files.

Use icon("home") inside HTML, and BUTTON_ICONS to put icons on Streamlit buttons.
"""

from urllib.parse import quote

# Inner SVG shapes. Style: 24x24 grid, round caps and joins, drawn as outlines.
ICONS: dict[str, str] = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9v11a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "file": (
        '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h6"/>'
    ),
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "quiz": (
        '<rect x="5" y="4" width="14" height="17" rx="2"/>'
        '<rect x="9" y="2" width="6" height="4" rx="1"/><path d="m9 14 2 2 4-4"/>'
    ),
    "code": '<path d="m8 8-4 4 4 4"/><path d="m16 8 4 4-4 4"/><path d="m14 5-4 14"/>',
    "plus": '<path d="M12 5v14"/><path d="M5 12h14"/>',
    "cap": (
        '<path d="M12 4 2 9l10 5 10-5-10-5z"/>'
        '<path d="M6 11.5V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-4.5"/><path d="M22 9v6"/>'
    ),
    "sparkle": (
        '<path d="M11 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>'
        '<path d="M19 3v4"/><path d="M17 5h4"/>'
    ),
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "trash": (
        '<path d="M3 6h18"/><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/>'
        '<path d="m19 6-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
        '<path d="M10 11v6"/><path d="M14 11v6"/>'
    ),
    "check": '<path d="m5 12.5 4.5 4.5L19 7"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 2.5 2.5 4.5-5"/>',
    "alert": (
        '<path d="m10.3 3.9-8.2 14A2 2 0 0 0 3.8 21h16.4a2 2 0 0 0 1.7-3.1l-8.2-14a2 2 0 0 0-3.4 0z"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "arrow-right": '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    "send": '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
}

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="black" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">'
    "{body}</svg>"
)


def svg_markup(name: str, stroke_width: float = 1.8) -> str:
    """The complete SVG text of an icon (used for the CSS masks and for previews)."""
    return _SVG.format(width=stroke_width, body=ICONS[name])


def _url(name: str) -> str:
    return f'url("data:image/svg+xml,{quote(svg_markup(name))}")'


def icon(name: str) -> str:
    """HTML for an icon that can be placed inside any markdown/HTML text."""
    if name not in ICONS:
        raise KeyError(f"Unknown icon: {name}")
    return f"<span class='ico ico-{name}'></span>"


# (CSS selector of the Streamlit button's container, icon name, position)
BUTTON_ICONS: list[tuple[str, str, str]] = [
    (".st-key-new_chat", "plus", "before"),
    (".st-key-nav_home", "home", "before"),
    (".st-key-nav_chat", "chat", "before"),
    (".st-key-nav_documents", "file", "before"),
    (".st-key-nav_quiz", "quiz", "before"),
    (".st-key-nav_python", "code", "before"),
    ('[class*="st-key-convo_"]', "chat", "before"),
    ('[class*="st-key-convopy_"]', "code", "before"),
    ('[class*="st-key-delc_"]', "x", "before"),
    ('[class*="st-key-delete_"]', "trash", "before"),
    ('[class*="st-key-open_"]', "arrow-right", "after"),
    ('[class*="st-key-home_ask_"]', "arrow-right", "after"),
    (".st-key-py_new", "plus", "before"),
    (".st-key-py_send", "send", "before"),
]

_MASK = (
    "content:''; display:inline-block; flex:none; width:1.15em; height:1.15em;"
    "background-color: currentColor;"
    "-webkit-mask-repeat:no-repeat; mask-repeat:no-repeat;"
    "-webkit-mask-position:center; mask-position:center;"
    "-webkit-mask-size:contain; mask-size:contain;"
)


def _mask(name: str) -> str:
    return f"-webkit-mask-image:{_url(name)}; mask-image:{_url(name)};"


def icon_css() -> str:
    """All CSS needed for icons: the .ico spans, button icons and chat avatars."""
    rules = [
        ".ico { display:inline-block; width:1.2em; height:1.2em; vertical-align:-0.22em;"
        "flex:none; background-color: currentColor;"
        "-webkit-mask-repeat:no-repeat; mask-repeat:no-repeat;"
        "-webkit-mask-position:center; mask-position:center;"
        "-webkit-mask-size:contain; mask-size:contain; }"
    ]
    rules += [f".ico-{name} {{ {_mask(name)} }}" for name in ICONS]

    for selector, name, position in BUTTON_ICONS:
        gap = "margin-left:.5rem;" if position == "after" else "margin-right:.6rem;"
        rules.append(f"{selector} button::{position} {{ {_MASK} {gap} {_mask(name)} }}")
    # Buttons that show only an icon
    for selector in ('[class*="st-key-delc_"]', '[class*="st-key-delete_"]'):
        rules.append(f"{selector} button p {{ display:none; }}")
        rules.append(f"{selector} button::before {{ margin-right:0; }}")
    # A selected document shows a check mark
    rules.append(
        f'[class*="st-key-select_"] button:disabled::before {{ {_MASK} margin-right:.4rem;'
        f"{_mask('check')} }}"
    )

    # Chat avatars: hide Streamlit's default glyph and draw our own icon
    rules.append(
        '[data-testid^="stChatMessageAvatar"] { display:flex !important;'
        "align-items:center; justify-content:center; border-radius:10px !important;"
        "color:#fff !important; }"
    )
    rules.append('[data-testid^="stChatMessageAvatar"] > * { display:none !important; }')
    rules.append(
        '[data-testid^="stChatMessageAvatar"]::after { content:""; width:20px; height:20px;'
        "background-color:#fff; -webkit-mask-repeat:no-repeat; mask-repeat:no-repeat;"
        "-webkit-mask-position:center; mask-position:center;"
        "-webkit-mask-size:contain; mask-size:contain; }"
    )
    rules.append(
        '[data-testid="stChatMessageAvatarUser"] { background:#64748B !important; }'
        f'[data-testid="stChatMessageAvatarUser"]::after {{ {_mask("user")} }}'
    )
    rules.append(
        '[data-testid="stChatMessageAvatarAssistant"],'
        '[data-testid="stChatMessageAvatarCustom"] {'
        "background: linear-gradient(135deg,#4F8BFF,#8B5CF6) !important; }"
        '[data-testid="stChatMessageAvatarAssistant"]::after,'
        f'[data-testid="stChatMessageAvatarCustom"]::after {{ {_mask("sparkle")} }}'
    )
    return "\n".join(rules)
