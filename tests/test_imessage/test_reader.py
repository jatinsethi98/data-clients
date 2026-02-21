"""Tests for iMessage reader."""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from data_clients.imessage.reader import ChatDBReader, APPLE_EPOCH_OFFSET
from data_clients.exceptions import IMessageReadError


@pytest.fixture
def chat_db(tmp_path):
    """Create a minimal chat.db for testing."""
    db_path = tmp_path / "chat.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY,
            guid TEXT,
            text TEXT,
            date INTEGER,
            is_from_me INTEGER DEFAULT 0,
            is_read INTEGER DEFAULT 0,
            service TEXT,
            cache_has_attachments INTEGER DEFAULT 0,
            associated_message_type INTEGER DEFAULT 0,
            associated_message_guid TEXT,
            thread_originator_guid TEXT,
            handle_id INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE handle (
            ROWID INTEGER PRIMARY KEY,
            id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE chat (
            ROWID INTEGER PRIMARY KEY,
            guid TEXT,
            chat_identifier TEXT,
            display_name TEXT,
            service_name TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE chat_message_join (
            chat_id INTEGER,
            message_id INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE chat_handle_join (
            chat_id INTEGER,
            handle_id INTEGER
        )
    """)

    # Insert test data
    now = datetime.now()
    apple_ts = int(now.timestamp() - APPLE_EPOCH_OFFSET)

    conn.execute("INSERT INTO handle VALUES (1, '+15551234567')")
    conn.execute("INSERT INTO chat VALUES (1, 'iMessage;+15551234567', '+15551234567', '', 'iMessage')")
    conn.execute(
        "INSERT INTO message VALUES (1, 'msg-guid-1', 'Hello!', ?, 0, 1, 'iMessage', 0, 0, '', '', 1)",
        (apple_ts,),
    )
    conn.execute("INSERT INTO chat_message_join VALUES (1, 1)")
    conn.execute("INSERT INTO chat_handle_join VALUES (1, 1)")
    conn.commit()
    conn.close()
    return db_path


def test_fetch_messages(chat_db):
    reader = ChatDBReader(db_path=chat_db)
    messages = reader.fetch_messages(days=1)
    assert len(messages) >= 1
    assert messages[0]["text"] == "Hello!"
    assert messages[0]["handle_id"] == "+15551234567"


def test_fetch_conversations(chat_db):
    reader = ChatDBReader(db_path=chat_db)
    convos = reader.fetch_conversations(days=1)
    assert len(convos) >= 1
    assert convos[0]["chat_identifier"] == "+15551234567"


def test_get_message_count(chat_db):
    reader = ChatDBReader(db_path=chat_db)
    count = reader.get_message_count(days=1)
    assert count >= 1


def test_missing_db():
    reader = ChatDBReader(db_path=Path("/nonexistent/chat.db"))
    with pytest.raises(IMessageReadError, match="not found"):
        reader.fetch_messages()


def test_excluded_contacts(chat_db):
    reader = ChatDBReader(db_path=chat_db)
    convos = reader.fetch_conversations(days=1, excluded_contacts=["+15551234567"])
    assert len(convos) == 0
