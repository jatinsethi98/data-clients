"""Read-only access to macOS Messages chat.db."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from data_clients.exceptions import IMessageReadError

logger = logging.getLogger(__name__)

CHAT_DB_PATH = Path.home() / "Library" / "Messages" / "chat.db"

# Apple's Core Data epoch offset (2001-01-01 vs 1970-01-01)
APPLE_EPOCH_OFFSET = 978307200


class ChatDBReader:
    """Read-only connection to the macOS Messages database."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or CHAT_DB_PATH
        self._nanoseconds: bool | None = None

    def _connect(self) -> sqlite3.Connection:
        """Open a read-only connection to chat.db."""
        if not self.db_path.exists():
            raise IMessageReadError(
                f"Messages database not found at {self.db_path}. "
                "Make sure you're running on macOS with Messages configured."
            )
        try:
            uri = f"file:{self.db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            err = str(e).lower()
            if "unable to open" in err or "authorization denied" in err:
                raise IMessageReadError(
                    "Cannot open chat.db — Full Disk Access is required. "
                    "Go to System Settings > Privacy & Security > Full Disk Access "
                    "and enable it for your terminal application."
                ) from e
            raise IMessageReadError(f"Failed to open chat.db: {e}") from e

    def _detect_timestamp_format(self, conn: sqlite3.Connection) -> bool:
        """Detect if timestamps are in nanoseconds (newer macOS) or seconds."""
        if self._nanoseconds is not None:
            return self._nanoseconds
        row = conn.execute("SELECT MAX(ABS(date)) FROM message").fetchone()
        max_date = row[0] if row and row[0] else 0
        self._nanoseconds = max_date > 1e12
        return self._nanoseconds

    def _convert_timestamp(self, apple_ts: int | None, conn: sqlite3.Connection) -> str:
        """Convert Apple timestamp to ISO 8601 string."""
        if apple_ts is None or apple_ts == 0:
            return ""
        ts = apple_ts
        if self._detect_timestamp_format(conn):
            ts = ts / 1e9
        unix_ts = ts + APPLE_EPOCH_OFFSET
        try:
            return datetime.fromtimestamp(unix_ts).isoformat()
        except (OSError, ValueError):
            return ""

    def _apple_ts_from_datetime(self, dt: datetime, conn: sqlite3.Connection) -> int:
        """Convert a datetime to an Apple timestamp for queries."""
        unix_ts = dt.timestamp()
        apple_ts = unix_ts - APPLE_EPOCH_OFFSET
        if self._detect_timestamp_format(conn):
            apple_ts = int(apple_ts * 1e9)
        return int(apple_ts)

    def fetch_conversations(
        self,
        days: int = 1,
        limit: int = 100,
        excluded_contacts: list[str] | None = None,
    ) -> list[dict]:
        """Fetch recent conversations with participant info."""
        conn = self._connect()
        try:
            since = datetime.now() - timedelta(days=days)
            apple_since = self._apple_ts_from_datetime(since, conn)

            rows = conn.execute(
                """
                SELECT DISTINCT
                    c.ROWID as chat_id,
                    c.guid as chat_guid,
                    c.chat_identifier,
                    c.display_name,
                    c.service_name
                FROM chat c
                JOIN chat_message_join cmj ON cmj.chat_id = c.ROWID
                JOIN message m ON m.ROWID = cmj.message_id
                WHERE m.date > ?
                ORDER BY m.date DESC
                LIMIT ?
                """,
                (apple_since, limit),
            ).fetchall()

            conversations = []
            for row in rows:
                chat_guid = row["chat_guid"]
                chat_id = row["chat_id"]

                participants = self._get_participants(conn, chat_id)

                if excluded_contacts:
                    identifier = row["chat_identifier"] or ""
                    if any(exc in identifier for exc in excluded_contacts):
                        continue
                    if any(
                        exc in p for p in participants for exc in excluded_contacts
                    ):
                        continue

                is_group = len(participants) > 1 or bool(row["display_name"])

                conversations.append({
                    "chat_guid": chat_guid,
                    "chat_identifier": row["chat_identifier"] or "",
                    "display_name": row["display_name"] or "",
                    "is_group": is_group,
                    "service": row["service_name"] or "",
                    "participant_ids": participants,
                })

            return conversations
        finally:
            conn.close()

    def fetch_messages(
        self,
        chat_guid: str | None = None,
        days: int = 1,
        limit: int = 500,
    ) -> list[dict]:
        """Fetch messages, optionally filtered by conversation."""
        conn = self._connect()
        try:
            since = datetime.now() - timedelta(days=days)
            apple_since = self._apple_ts_from_datetime(since, conn)

            if chat_guid:
                rows = conn.execute(
                    """
                    SELECT
                        m.ROWID,
                        m.guid,
                        m.text,
                        m.date,
                        m.is_from_me,
                        m.is_read,
                        m.service,
                        m.cache_has_attachments,
                        m.associated_message_type,
                        m.associated_message_guid,
                        m.thread_originator_guid,
                        h.id as handle_id
                    FROM message m
                    JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
                    JOIN chat c ON c.ROWID = cmj.chat_id
                    LEFT JOIN handle h ON h.ROWID = m.handle_id
                    WHERE c.guid = ? AND m.date > ?
                    ORDER BY m.date ASC
                    LIMIT ?
                    """,
                    (chat_guid, apple_since, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        m.ROWID,
                        m.guid,
                        m.text,
                        m.date,
                        m.is_from_me,
                        m.is_read,
                        m.service,
                        m.cache_has_attachments,
                        m.associated_message_type,
                        m.associated_message_guid,
                        m.thread_originator_guid,
                        h.id as handle_id
                    FROM message m
                    LEFT JOIN handle h ON h.ROWID = m.handle_id
                    WHERE m.date > ?
                    ORDER BY m.date ASC
                    LIMIT ?
                    """,
                    (apple_since, limit),
                ).fetchall()

            messages = []
            for row in rows:
                messages.append({
                    "rowid": row["ROWID"],
                    "guid": row["guid"],
                    "text": row["text"] or "",
                    "date": self._convert_timestamp(row["date"], conn),
                    "is_from_me": bool(row["is_from_me"]),
                    "is_read": bool(row["is_read"]),
                    "service": row["service"] or "",
                    "has_attachments": bool(row["cache_has_attachments"]),
                    "associated_message_type": row["associated_message_type"] or 0,
                    "associated_message_guid": row["associated_message_guid"] or "",
                    "thread_originator_guid": row["thread_originator_guid"] or "",
                    "handle_id": row["handle_id"] or "",
                })

            return messages
        finally:
            conn.close()

    def _get_participants(self, conn: sqlite3.Connection, chat_id: int) -> list[str]:
        """Get participant handle IDs for a chat."""
        rows = conn.execute(
            """
            SELECT h.id
            FROM handle h
            JOIN chat_handle_join chj ON chj.handle_id = h.ROWID
            WHERE chj.chat_id = ?
            """,
            (chat_id,),
        ).fetchall()
        return [row["id"] for row in rows]

    def get_message_count(self, days: int = 1) -> int:
        """Count messages in the last N days."""
        conn = self._connect()
        try:
            since = datetime.now() - timedelta(days=days)
            apple_since = self._apple_ts_from_datetime(since, conn)
            row = conn.execute(
                "SELECT COUNT(*) FROM message WHERE date > ?",
                (apple_since,),
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
