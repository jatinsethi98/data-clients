"""Data models for the iMessage module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedMessage:
    """A single parsed message from chat.db."""

    message_guid: str
    sender_id: str
    sender_is_me: bool
    text: str
    date: str  # ISO 8601
    service: str  # "iMessage" or "SMS"
    is_read: bool
    has_attachments: bool
    is_tapback: bool
    is_edit: bool
    thread_originator: str | None = None


@dataclass
class Conversation:
    """A chat/conversation from chat.db."""

    chat_guid: str
    chat_identifier: str
    display_name: str
    is_group: bool
    service: str
    participant_ids: list[str] = field(default_factory=list)
    messages: list[ParsedMessage] = field(default_factory=list)
    last_message_date: str = ""


@dataclass
class MessageSummary:
    """A Claude-generated summary of messages."""

    conversation_id: int | None  # None for daily briefings
    summary_type: str  # "conversation", "daily"
    date_range_start: str
    date_range_end: str
    message_count: int
    summary_text: str
    key_topics: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
