"""Central settings for Smart University AI.

Names, navigation, feature cards and every model/RAG parameter live here,
so the UI code has no hard-coded text and the parameters are easy to explain
and tune. Secrets and provider details come from the .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # read the .env file (API key and model settings)

APP_NAME = "Smart University AI"
APP_TAGLINE = "Your study assistant"

USER_NAME = os.getenv("USER_NAME", "Prince")
USER_FULL_NAME = os.getenv("USER_FULL_NAME", "Prince Heritier")
USER_SUBTITLE = "Year 3 • IT"

# Sidebar navigation. "id" is used for widget keys and styling.
NAV_ITEMS: list[dict] = [
    {"id": "home", "page": "Home", "icon": "home"},
    {"id": "chat", "page": "Chat", "icon": "chat"},
    {"id": "documents", "page": "Documents", "icon": "file"},
    {"id": "quiz", "page": "Quiz", "icon": "quiz"},
    {"id": "python", "page": "Python Assistant", "icon": "code"},
]

# The five main features shown as cards on the home screen.
FEATURES: list[dict] = [
    {
        "id": "chat",
        "icon": "chat",
        "color": "#5B5BF0",
        "title": "AI Chat",
        "description": "Ask questions and learn anything.",
        "page": "Chat",
        "tint": "rgba(91, 91, 240, 0.14)",
    },
    {
        "id": "ask_docs",
        "icon": "search",
        "color": "#0EA5E9",
        "title": "Ask My Documents",
        "description": "Upload notes and ask questions.",
        "page": "Documents",
        "mode": "Ask",
        "tint": "rgba(14, 165, 233, 0.14)",
    },
    {
        "id": "summarize",
        "icon": "file",
        "color": "#10B981",
        "title": "Summarize PDF",
        "description": "Turn long notes into simple summaries.",
        "page": "Documents",
        "mode": "Summarize",
        "tint": "rgba(16, 185, 129, 0.14)",
    },
    {
        "id": "quiz",
        "icon": "quiz",
        "color": "#A855F7",
        "title": "Generate Quiz",
        "description": "Create revision questions from your notes.",
        "page": "Quiz",
        "tint": "rgba(168, 85, 247, 0.14)",
    },
    {
        "id": "python",
        "icon": "code",
        "color": "#F59E0B",
        "title": "Python Assistant",
        "description": "Learn, debug and write Python code.",
        "page": "Python Assistant",
        "tint": "rgba(245, 158, 11, 0.14)",
    },
]

# ---------- LLM settings ----------
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash")
LLM_TIMEOUT = 90.0  # seconds to wait for one answer
LLM_MAX_RETRIES = 1  # automatic retries on temporary failures

# Model parameters (explained in docs/CAT_REPORT.md, tuned with the evaluator)
LLM_TEMPERATURE = 0.7  # AI Chat: 0 = very predictable, 1+ = more creative
LLM_MAX_TOKENS = 2048  # maximum length of one answer
CHAT_HISTORY_LIMIT = 20  # how many recent messages the model remembers
MAX_MESSAGE_CHARS = 20000  # longest message a user may send
MAX_CODE_CHARS = 15000  # longest code snippet in the Python Assistant form

# ---------- Python Assistant settings ----------
PYTHON_TEMPERATURE = 0.3  # code help should be precise
PYTHON_MAX_TOKENS = 3000  # room for explanation + corrected code

# ---------- Storage ----------
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"  # the original PDFs
PROCESSED_DIR = DATA_DIR / "processed"  # extracted text, one JSON file per PDF
SUMMARIES_DIR = DATA_DIR / "summaries"  # saved summaries, one JSON file per PDF
DB_PATH = DATA_DIR / "app.db"  # SQLite: saved conversations

# ---------- Document settings ----------
MAX_PDF_SIZE_MB = 20  # reject bigger files
MAX_PDF_PAGES = 300  # reject very long documents
MIN_TEXT_CHARS = 50  # below this, the PDF is treated as "no extractable text"

# ---------- RAG settings ----------
VECTOR_DIR = BASE_DIR / "vector_store"
COLLECTION_NAME = "documents"

# Embedding model: small, fast, runs locally, 384-dimensional vectors
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 1000  # maximum characters per chunk
CHUNK_OVERLAP = 200  # characters shared between neighbouring chunks
MIN_CHUNK_CHARS = 30  # ignore tiny fragments
TOP_K = 4  # how many chunks to retrieve per question
RAG_TEMPERATURE = 0.2  # low = stick to the document, less creativity
MIN_SIMILARITY = 0.25  # chunks scoring below this are ignored

# ---------- Summarizer settings ----------
SUMMARY_TEMPERATURE = 0.3  # low: faithful to the document
SUMMARY_MAX_TOKENS = 3000  # room for the final six-section summary
NOTES_MAX_TOKENS = 1500  # per-section notes
SUMMARY_SECTION_CHARS = 12000  # about 3,000 tokens per section

# ---------- Quiz settings ----------
QUIZ_TEMPERATURE = 0.5  # some variety in questions, but still faithful to the text
QUIZ_MAX_TOKENS = 4000  # enough for 15 questions with explanations
QUIZ_CONTEXT_CHARS = 14000  # how much document text the AI sees (about 3,500 tokens)
QUIZ_COUNTS = [5, 10, 15]
QUIZ_DIFFICULTIES = ["Easy", "Medium", "Hard"]
