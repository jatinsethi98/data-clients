"""Read-only access to Safari and Chrome history databases."""

from __future__ import annotations

import logging
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from data_clients.exceptions import BrowserHistoryReadError

logger = logging.getLogger(__name__)

SAFARI_HISTORY_PATH = Path.home() / "Library" / "Safari" / "History.db"
CHROME_BASE_PATH = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"

# Seconds from 1970-01-01 to 2001-01-01 (Safari/WebKit epoch).
APPLE_EPOCH_OFFSET = 978307200
# Seconds from 1601-01-01 to 1970-01-01 (Chrome epoch).
CHROME_EPOCH_OFFSET = 11644473600


class BrowserHistoryReader:
    """Read browser history from local Safari and Chrome SQLite databases."""

    def __init__(self) -> None:
        self.last_errors: dict[str, str] = {}

    def fetch_visits(
        self,
        days: int = 30,
        limit: int = 5000,
        include_safari: bool = True,
        include_chrome: bool = True,
    ) -> list[dict]:
        """Fetch visits from enabled browser sources.

        The `limit` is applied per enabled source.
        """
        effective_days = self._clamp_days(days)
        per_source_limit = max(1, limit)
        visits: list[dict] = []
        errors: list[BrowserHistoryReadError] = []
        self.last_errors = {}

        if include_safari:
            try:
                visits.extend(self._fetch_safari_visits(effective_days, per_source_limit))
            except BrowserHistoryReadError as e:
                errors.append(e)
                self.last_errors["safari"] = str(e)
                logger.warning("Safari history fetch failed: %s", e)
        if include_chrome:
            try:
                visits.extend(self._fetch_chrome_visits(effective_days, per_source_limit))
            except BrowserHistoryReadError as e:
                errors.append(e)
                self.last_errors["chrome"] = str(e)
                logger.warning("Chrome history fetch failed: %s", e)

        if not visits and errors:
            raise errors[0]

        visits.sort(key=lambda v: v.get("visited_at", ""), reverse=True)
        return visits

    @staticmethod
    def _clamp_days(days: int) -> int:
        """Browser ingestion is hard-capped to 30 days."""
        return max(1, min(days, 30))

    def _fetch_safari_visits(self, days: int, limit: int) -> list[dict]:
        """Fetch recent Safari visits from History.db."""
        if not SAFARI_HISTORY_PATH.exists():
            logger.info("Safari history DB not found at %s", SAFARI_HISTORY_PATH)
            return []

        since = datetime.now() - timedelta(days=days)
        safari_since = since.timestamp() - APPLE_EPOCH_OFFSET

        try:
            conn = sqlite3.connect(f"file:{SAFARI_HISTORY_PATH}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise BrowserHistoryReadError(
                "Cannot open Safari History.db. "
                "Enable Full Disk Access for your terminal if needed."
            ) from e

        try:
            item_columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(history_items)").fetchall()
            }
            visit_columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(history_visits)").fetchall()
            }
            if "title" in visit_columns:
                title_expr = "COALESCE(hv.title, '')"
            elif "title" in item_columns:
                title_expr = "COALESCE(hi.title, '')"
            else:
                title_expr = "''"
            visit_count_expr = "COALESCE(hi.visit_count, 1)" if "visit_count" in item_columns else "1"

            rows = conn.execute(
                f"""
                SELECT
                    hv.id AS visit_id,
                    hv.visit_time AS visit_time,
                    COALESCE(hi.url, '') AS url,
                    {title_expr} AS title,
                    {visit_count_expr} AS visit_count
                FROM history_visits hv
                JOIN history_items hi ON hi.id = hv.history_item
                WHERE hv.visit_time >= ?
                ORDER BY hv.visit_time DESC
                LIMIT ?
                """,
                (safari_since, limit),
            ).fetchall()
        except sqlite3.Error as e:
            raise BrowserHistoryReadError(f"Failed querying Safari history: {e}") from e
        finally:
            conn.close()

        visits: list[dict] = []
        for row in rows:
            visited_at = self._safari_ts_to_iso(row["visit_time"])
            if not visited_at:
                continue
            visits.append({
                "source_type": "safari",
                "profile": "Default",
                "source_visit_id": str(row["visit_id"]),
                "url": row["url"],
                "title": row["title"],
                "visit_count": int(row["visit_count"] or 1),
                "transition": "",
                "visited_at": visited_at,
            })

        return visits

    def _fetch_chrome_visits(self, days: int, limit: int) -> list[dict]:
        """Fetch recent visits across Chrome profiles."""
        history_paths = self._chrome_history_paths()
        if not history_paths:
            logger.info("Chrome history DBs not found under %s", CHROME_BASE_PATH)
            return []

        since = datetime.now() - timedelta(days=days)
        chrome_since = int((since.timestamp() + CHROME_EPOCH_OFFSET) * 1_000_000)

        visits: list[dict] = []
        per_profile_limit = max(50, limit // max(1, len(history_paths)))

        for history_path in history_paths:
            profile = history_path.parent.name
            db_copy = self._copy_chrome_db(history_path)
            if not db_copy:
                continue
            conn: sqlite3.Connection | None = None
            try:
                conn = sqlite3.connect(str(db_copy))
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT
                        v.id AS visit_id,
                        v.visit_time AS visit_time,
                        v.transition AS transition,
                        COALESCE(u.url, '') AS url,
                        COALESCE(u.title, '') AS title,
                        COALESCE(u.visit_count, 1) AS visit_count
                    FROM visits v
                    JOIN urls u ON u.id = v.url
                    WHERE v.visit_time >= ?
                    ORDER BY v.visit_time DESC
                    LIMIT ?
                    """,
                    (chrome_since, per_profile_limit),
                ).fetchall()
            except sqlite3.Error as e:
                logger.warning("Failed querying Chrome history (%s): %s", profile, e)
                rows = []
            finally:
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass
                db_copy.unlink(missing_ok=True)

            for row in rows:
                visited_at = self._chrome_ts_to_iso(row["visit_time"])
                if not visited_at:
                    continue
                visits.append({
                    "source_type": "chrome",
                    "profile": profile,
                    "source_visit_id": str(row["visit_id"]),
                    "url": row["url"],
                    "title": row["title"],
                    "visit_count": int(row["visit_count"] or 1),
                    "transition": str(row["transition"] or ""),
                    "visited_at": visited_at,
                })

        visits.sort(key=lambda v: v.get("visited_at", ""), reverse=True)
        return visits[:limit]

    @staticmethod
    def _chrome_history_paths() -> list[Path]:
        if not CHROME_BASE_PATH.exists():
            return []

        paths = []
        for child in CHROME_BASE_PATH.iterdir():
            if not child.is_dir():
                continue
            history = child / "History"
            if not history.exists():
                continue
            if child.name in {"System Profile"}:
                continue
            paths.append(history)

        paths.sort()
        return paths

    @staticmethod
    def _copy_chrome_db(path: Path) -> Path | None:
        """Chrome locks History DB; query a temporary copy instead."""
        try:
            with tempfile.NamedTemporaryFile(prefix="chrome-history-", suffix=".db", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            shutil.copy2(path, tmp_path)
            return tmp_path
        except Exception as e:
            logger.warning("Failed to copy Chrome history DB %s: %s", path, e)
            return None

    @staticmethod
    def _safari_ts_to_iso(ts: float | int | None) -> str:
        if ts is None:
            return ""
        try:
            unix_ts = float(ts) + APPLE_EPOCH_OFFSET
            return datetime.fromtimestamp(unix_ts).isoformat()
        except (ValueError, OSError, OverflowError):
            return ""

    @staticmethod
    def _chrome_ts_to_iso(ts: int | None) -> str:
        if ts is None:
            return ""
        try:
            unix_ts = (int(ts) / 1_000_000) - CHROME_EPOCH_OFFSET
            return datetime.fromtimestamp(unix_ts).isoformat()
        except (ValueError, OSError, OverflowError):
            return ""
