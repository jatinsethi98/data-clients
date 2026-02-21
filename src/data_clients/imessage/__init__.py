"""iMessage data access (macOS only)."""

from data_clients.imessage.reader import ChatDBReader
from data_clients.imessage.sender import send_message, send_to_group, send_attachment
from data_clients.imessage.models import ParsedMessage, Conversation, MessageSummary

__all__ = [
    "ChatDBReader",
    "send_message",
    "send_to_group",
    "send_attachment",
    "ParsedMessage",
    "Conversation",
    "MessageSummary",
]
