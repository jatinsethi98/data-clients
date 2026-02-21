"""Gmail API email fetching utilities — low-level API.

Use this when you have a raw Google API ``service`` object and want
lightweight iteration without the full ``Gmail`` class.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterator

from googleapiclient.discovery import Resource

from data_clients.exceptions import GmailFetchError

logger = logging.getLogger(__name__)


def fetch_messages(
    service: Resource,
    days: int = 1,
    max_results: int = 200,
    skip_labels: list[str] | None = None,
    include_labels: list[str] | None = None,
) -> Iterator[dict]:
    """Fetch messages from Gmail API for the last N days.

    Yields raw message dicts (format=full) for parsing.
    """
    after_date = datetime.now() - timedelta(days=days)
    query = f"after:{after_date.strftime('%Y/%m/%d')}"

    if skip_labels:
        for lbl in skip_labels:
            query += f" -label:{lbl}"

    logger.info(f"Fetching emails with query: {query}")

    try:
        message_ids = _list_message_ids(service, query, max_results, include_labels)
    except Exception as e:
        raise GmailFetchError(f"Failed to list messages: {e}") from e

    logger.info(f"Found {len(message_ids)} messages")

    for msg_id in message_ids:
        try:
            full_message = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
            yield full_message
        except Exception as e:
            logger.warning(f"Failed to fetch message {msg_id}: {e}")
            continue


def _list_message_ids(
    service: Resource,
    query: str,
    max_results: int,
    label_ids: list[str] | None = None,
) -> list[str]:
    """List message IDs matching the query, handling pagination."""
    ids: list[str] = []
    page_token = None

    while len(ids) < max_results:
        kwargs: dict = {
            "userId": "me",
            "q": query,
            "maxResults": min(max_results - len(ids), 100),
        }
        if page_token:
            kwargs["pageToken"] = page_token
        if label_ids:
            kwargs["labelIds"] = label_ids

        response = service.users().messages().list(**kwargs).execute()
        messages = response.get("messages", [])

        if not messages:
            break

        ids.extend(msg["id"] for msg in messages)
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return ids[:max_results]


def get_account_email(service: Resource) -> str:
    """Get the email address of the authenticated account."""
    try:
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:
        return ""
