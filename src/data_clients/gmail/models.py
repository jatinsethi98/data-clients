"""Data models for the Gmail module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedEmail:
    """Structured representation of a Gmail message."""

    gmail_message_id: str
    thread_id: str
    subject: str
    sender_name: str
    sender_email: str
    recipients: list[str]
    date: str
    body_text: str
    body_snippet: str
    labels: list[str]
    has_attachments: bool
    is_read: bool


@dataclass
class EmailSummary:
    """A generated summary of emails."""

    account_id: str | None
    summary_type: str  # "daily", "weekly", "cross_account"
    date_range_start: str
    date_range_end: str
    email_count: int
    summary_text: str
    key_topics: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
