"""SQLite storage for saved conversations (AI Chat and Python Assistant)."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config.settings import DB_PATH


@contextmanager
def _connect():
    """Open a short-lived connection (safe with Streamlit's re-runs and threads)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id);
            """
        )


def create_conversation(title: str, mode: str) -> int:
    """Start a new conversation and return its ID."""
    now = _now()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO conversations (title, mode, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, mode, now, now),
        )
        return int(cursor.lastrowid)


def add_message(conversation_id: int, role: str, content: str) -> None:
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
        )


def get_messages(conversation_id: int) -> list[dict]:
    """The messages of a conversation, oldest first, as {'role', 'content'} dicts."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def get_conversation(conversation_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, title, mode, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    return dict(row) if row else None


def list_conversations(limit: int = 30) -> list[dict]:
    """Most recently used conversations first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, mode, created_at, updated_at FROM conversations "
            "ORDER BY updated_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_conversation(conversation_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
