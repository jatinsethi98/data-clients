"""Read-only access to WhatsApp ChatStorage.sqlite on macOS."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from data_clients.exceptions import WhatsAppAccountNotFoundError, WhatsAppReadError

logger = logging.getLogger(__name__)

# WhatsApp for Mac stores ChatStorage.sqlite in Group Containers
WHATSAPP_GROUP_CONTAINER = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "group.net.whatsapp.WhatsApp.shared"
    / "ChatStorage.sqlite"
)

# Older installs may use iCloud Mobile Documents
WHATSAPP_MOBILE_DOCUMENTS = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "68Y0128N3~net~whatsapp~WhatsApp"
)

# Core Data epoch (2001-01-01) — same offset as iMessage
APPLE_EPOCH_OFFSET = 978307200

# WhatsApp "status" session type — not a real chat
_STATUS_SESSION_TYPE = 3


def _find_db_paths() -> list[Path]:
    """Auto-discover ChatStorage.sqlite locations on this Mac."""
    paths: list[Path] = []

    # Primary: Group Containers (modern WhatsApp for Mac)
    if WHATSAPP_GROUP_CONTAINER.exists():
        paths.append(WHATSAPP_GROUP_CONTAINER)

    # Fallback: iCloud Mobile Documents (older installs)
    if WHATSAPP_MOBILE_DOCUMENTS.exists():
        for account_dir in WHATSAPP_MOBILE_DOCUMENTS.glob("**/ChatStorage.sqlite"):
            if account_dir not in paths:
                paths.append(account_dir)

    return paths


class WhatsAppDBReader:
    """Read-only access to WhatsApp ChatStorage.sqlite on macOS."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _resolve_db_path(self) -> Path:
        """Find the ChatStorage.sqlite to use."""
        if self.db_path:
            if not self.db_path.exists():
                raise WhatsAppReadError(
                    f"ChatStorage.sqlite not found at {self.db_path}."
                )
            return self.db_path

        paths = _find_db_paths()
        if not paths:
            raise WhatsAppAccountNotFoundError(
                "WhatsApp ChatStorage.sqlite not found. "
                "Ensure WhatsApp for Mac is installed. "
                f"Checked: {WHATSAPP_GROUP_CONTAINER}, {WHATSAPP_MOBILE_DOCUMENTS}"
            )
        return paths[0]

    def list_accounts(self) -> list[str]:
        """Return discovered ChatStorage.sqlite locations as account labels."""
        paths = _find_db_paths()
        if not paths:
            raise WhatsAppAccountNotFoundError(
                "WhatsApp ChatStorage.sqlite not found. "
                "Ensure WhatsApp for Mac is installed."
            )
        return [str(p) for p in paths]

    def fetch_conversations(
        self,
        days: int = 1,
        limit: int = 100,
        excluded_contacts: list[str] | None = None,
        account_ids: list[str] | None = None,
    ) -> list[dict]:
        """Fetch recent conversations.

        Each returned dict maps to the fields of
        data_clients.whatsapp.models.Conversation.
        """
        db_path = self._resolve_db_path()
        account_id = db_path.parent.name
        conn = self._connect(db_path)
        try:
            since_apple = self._datetime_to_apple_ts(
                datetime.now() - timedelta(days=days)
            )
            rows = conn.execute(
                """
                SELECT
                    s.Z_PK          AS session_pk,
                    s.ZPARTNERNAME  AS partner_name,
                    s.ZSESSIONTYPE  AS session_type,
                    s.ZCONTACTJID   AS contact_jid,
                    MAX(m.ZMESSAGEDATE) AS latest_date
                FROM ZWACHATSESSION s
                JOIN ZWAMESSAGE m ON m.ZCHATSESSION = s.Z_PK
                WHERE m.ZMESSAGEDATE > ?
                  AND s.ZSESSIONTYPE != ?
                GROUP BY s.Z_PK
                ORDER BY latest_date DESC
                LIMIT ?
                """,
                (since_apple, _STATUS_SESSION_TYPE, limit),
            ).fetchall()

            conversations = []
            for row in rows:
                partner_name = row["partner_name"] or ""

                if excluded_contacts and any(
                    exc.lower() in partner_name.lower()
                    for exc in excluded_contacts
                ):
                    continue

                session_pk = row["session_pk"]
                contact_jid = row["contact_jid"] or ""
                session_type = row["session_type"] or 0
                is_group = session_type == 1
                # Use ZCONTACTJID as stable identifier (survives renames)
                chat_guid = f"whatsapp:{contact_jid}" if contact_jid else f"whatsapp:pk:{session_pk}"

                participant_ids = []
                if is_group:
                    participant_ids = self._get_group_participants(
                        conn, session_pk
                    )

                conversations.append({
                    "chat_guid": chat_guid,
                    "chat_identifier": contact_jid or partner_name,
                    "display_name": partner_name,
                    "is_group": is_group,
                    "session_type": session_type,
                    "account_id": account_id,
                    "participant_ids": participant_ids,
                    "last_message_date": self._apple_ts_to_iso(row["latest_date"]),
                })

            return conversations
        finally:
            conn.close()

    def fetch_messages(
        self,
        chat_guid: str,
        days: int = 1,
        limit: int = 500,
    ) -> list[dict]:
        """Fetch messages for a single conversation.

        chat_guid format: "whatsapp:<jid>" or "whatsapp:pk:<session_pk>"
        """
        jid_or_pk = self._parse_chat_guid(chat_guid)
        db_path = self._resolve_db_path()
        account_id = db_path.parent.name
        conn = self._connect(db_path)
        try:
            # Resolve to session PK
            session_pk = self._resolve_session_pk(conn, jid_or_pk)

            since_apple = self._datetime_to_apple_ts(
                datetime.now() - timedelta(days=days)
            )
            rows = conn.execute(
                """
                SELECT
                    m.Z_PK          AS row_pk,
                    m.ZTEXT         AS text,
                    m.ZMESSAGEDATE  AS msg_date,
                    m.ZISFROMME     AS is_from_me,
                    m.ZFROMJID      AS from_jid,
                    m.ZTOJID        AS to_jid,
                    m.ZMESSAGETYPE  AS message_type,
                    m.ZPUSHNAME     AS push_name
                FROM ZWAMESSAGE m
                WHERE m.ZCHATSESSION = ?
                  AND m.ZMESSAGEDATE > ?
                ORDER BY m.ZMESSAGEDATE ASC
                LIMIT ?
                """,
                (session_pk, since_apple, limit),
            ).fetchall()
        finally:
            conn.close()

        messages = []
        for row in rows:
            msg_guid = f"{account_id}:{row['row_pk']}"
            is_from_me = bool(row["is_from_me"])
            sender_id = "me" if is_from_me else (row["from_jid"] or "")
            message_type = row["message_type"] or 0
            messages.append({
                "message_guid": msg_guid,
                "sender_id": sender_id,
                "sender_is_me": is_from_me,
                "sender_push_name": row["push_name"] or "",
                "text": row["text"] or "",
                "date": self._apple_ts_to_iso(row["msg_date"]),
                "message_type": message_type,
                "has_media": message_type != 0,
                "account_id": account_id,
            })
        return messages

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _connect(self, db_path: Path) -> sqlite3.Connection:
        if not db_path.exists():
            raise WhatsAppReadError(
                f"ChatStorage.sqlite not found at {db_path}."
            )
        try:
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            err = str(e).lower()
            if "unable to open" in err or "authorization denied" in err:
                raise WhatsAppReadError(
                    "Cannot open ChatStorage.sqlite — Full Disk Access is required. "
                    "Go to System Settings > Privacy & Security > Full Disk Access "
                    "and enable it for your terminal application."
                ) from e
            raise WhatsAppReadError(
                f"Failed to open ChatStorage.sqlite: {e}"
            ) from e

    def _resolve_session_pk(self, conn: sqlite3.Connection, jid_or_pk: str) -> int:
        """Resolve a JID or raw PK string to a ZWACHATSESSION.Z_PK."""
        if jid_or_pk.startswith("pk:"):
            return int(jid_or_pk[3:])
        # Look up by ZCONTACTJID
        row = conn.execute(
            "SELECT Z_PK FROM ZWACHATSESSION WHERE ZCONTACTJID = ?",
            (jid_or_pk,),
        ).fetchone()
        if not row:
            raise WhatsAppReadError(
                f"No WhatsApp session found for JID '{jid_or_pk}'."
            )
        return row["Z_PK"]

    def _get_group_participants(
        self, conn: sqlite3.Connection, session_pk: int
    ) -> list[str]:
        try:
            rows = conn.execute(
                "SELECT ZMEMBERJID FROM ZWAGROUPMEMBER WHERE ZCHATSESSION = ?",
                (session_pk,),
            ).fetchall()
            return [r["ZMEMBERJID"] for r in rows if r["ZMEMBERJID"]]
        except sqlite3.OperationalError:
            return []

    @staticmethod
    def _apple_ts_to_iso(apple_ts: float | int | None) -> str:
        if apple_ts is None or apple_ts == 0:
            return ""
        try:
            unix_ts = float(apple_ts) + APPLE_EPOCH_OFFSET
            return datetime.fromtimestamp(unix_ts).isoformat()
        except (OSError, ValueError, OverflowError):
            return ""

    @staticmethod
    def _datetime_to_apple_ts(dt: datetime) -> float:
        return dt.timestamp() - APPLE_EPOCH_OFFSET

    @staticmethod
    def _parse_chat_guid(chat_guid: str) -> str:
        """Parse 'whatsapp:<jid>' or 'whatsapp:pk:<session_pk>' into the identifier part."""
        if not chat_guid.startswith("whatsapp:"):
            raise WhatsAppReadError(
                f"Invalid WhatsApp chat_guid format: '{chat_guid}'. "
                "Expected 'whatsapp:<jid>' or 'whatsapp:pk:<session_pk>'."
            )
        return chat_guid[len("whatsapp:"):]
