"""WhatsApp data access (macOS iCloud sync only)."""

from data_clients.whatsapp.models import Conversation, MessageSummary, ParsedMessage
from data_clients.whatsapp.reader import WhatsAppDBReader
from data_clients.whatsapp.sender import send_message, compose_message

__all__ = [
    "WhatsAppDBReader",
    "send_message",
    "compose_message",
    "ParsedMessage",
    "Conversation",
    "MessageSummary",
]
