import time

import database.database as db


def test_conversation_roundtrip(storage):
    cid = db.create_conversation("Python loops", "chat")
    db.add_message(cid, "user", "What is a loop?")
    db.add_message(cid, "assistant", "A loop repeats code.")
    assert db.get_messages(cid) == [
        {"role": "user", "content": "What is a loop?"},
        {"role": "assistant", "content": "A loop repeats code."},
    ]
    assert db.get_conversation(cid)["title"] == "Python loops"
    assert db.get_conversation(cid)["mode"] == "chat"


def test_list_is_most_recent_first(storage):
    first = db.create_conversation("old", "chat")
    second = db.create_conversation("new", "python")
    assert [c["id"] for c in db.list_conversations()] == [second, first]
    time.sleep(1.1)  # timestamps have one-second resolution
    db.add_message(first, "user", "bump")
    assert db.list_conversations()[0]["id"] == first


def test_delete_removes_messages_too(storage):
    cid = db.create_conversation("x", "chat")
    db.add_message(cid, "user", "hello")
    db.delete_conversation(cid)
    assert db.get_conversation(cid) is None
    assert db.get_messages(cid) == []


def test_limit_and_unknown_ids(storage):
    for i in range(5):
        db.create_conversation(f"c{i}", "chat")
    assert len(db.list_conversations(limit=3)) == 3
    assert db.get_conversation(9999) is None
    assert db.get_messages(9999) == []


def test_init_is_safe_to_repeat(storage):
    cid = db.create_conversation("keep me", "chat")
    db.init_db()
    assert db.get_conversation(cid) is not None
