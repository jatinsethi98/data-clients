"""Parse Gmail API message payloads into structured data."""

from __future__ import annotations

import base64
import re
from email.utils import parseaddr

from bs4 import BeautifulSoup

from data_clients.gmail.models import ParsedEmail


def parse_message(raw_message: dict, max_body_length: int = 10000) -> ParsedEmail:
    """Extract structured data from a Gmail API message payload.

    This is a pure parsing function — no network calls. Works with raw
    message dicts from the Gmail API (format=full).
    """
    payload = raw_message.get("payload", {})
    headers = _extract_headers(payload)
    label_ids = raw_message.get("labelIds", [])

    sender_name, sender_email = _parse_sender(headers.get("from", ""))
    body_text = _extract_body(payload)

    if len(body_text) > max_body_length:
        body_text = body_text[:max_body_length]

    return ParsedEmail(
        gmail_message_id=raw_message["id"],
        thread_id=raw_message.get("threadId", ""),
        subject=headers.get("subject", "(no subject)"),
        sender_name=sender_name,
        sender_email=sender_email,
        recipients=_parse_recipients(headers.get("to", "")),
        date=headers.get("date", ""),
        body_text=body_text,
        body_snippet=body_text[:500] if body_text else "",
        labels=label_ids,
        has_attachments=_has_attachments(payload),
        is_read="UNREAD" not in label_ids,
    )


def _extract_headers(payload: dict) -> dict[str, str]:
    return {
        h["name"].lower(): h["value"]
        for h in payload.get("headers", [])
    }


def _parse_sender(from_header: str) -> tuple[str, str]:
    name, email = parseaddr(from_header)
    return name or email, email


def _parse_recipients(to_header: str) -> list[str]:
    if not to_header:
        return []
    return [addr.strip() for addr in to_header.split(",") if addr.strip()]


def _extract_body(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        return _decode_body_data(payload)

    if mime_type.startswith("multipart/"):
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                text = _decode_body_data(part)
                if text:
                    return text
        for part in parts:
            text = _extract_body(part)
            if text:
                return text

    if mime_type == "text/html":
        html = _decode_body_data(payload)
        return _strip_html(html) if html else ""

    return ""


def _decode_body_data(payload: dict) -> str:
    data = payload.get("body", {}).get("data", "")
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _has_attachments(payload: dict) -> bool:
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("filename"):
            return True
        if part.get("parts") and _has_attachments(part):
            return True
    return False
