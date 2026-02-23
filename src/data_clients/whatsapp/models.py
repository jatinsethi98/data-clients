"""Data models for the WhatsApp module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedMessage:
    """A single parsed WhatsApp message from ChatStorage.sqlite."""

    message_guid: str  # "{account_id}:{Z_PK}"
    sender_id: str  # ZFROMJID or "me"
    sender_is_me: bool
    sender_push_name: str  # ZPUSHNAME display name
    text: str
    date: str  # ISO 8601
    message_type: int  # 0=text, 1=image, 2=audio, 5=location, etc.
    has_media: bool
    account_id: str


@dataclass
class Conversation:
    """A WhatsApp chat session from ChatStorage.sqlite."""

    chat_guid: str  # "whatsapp:{account_id}:{session_pk}"
    chat_identifier: str
    display_name: str
    is_group: bool
    session_type: int  # 0=private, 1=group, 2=broadcast
    account_id: str
    participant_ids: list[str] = field(default_factory=list)
    messages: list[ParsedMessage] = field(default_factory=list)
    last_message_date: str = ""


@dataclass
class MessageSummary:
    """A Claude-generated summary of WhatsApp messages."""

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
