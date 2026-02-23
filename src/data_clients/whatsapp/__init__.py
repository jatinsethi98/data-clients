"""WhatsApp data access (macOS iCloud sync only)."""

from data_clients.whatsapp.models import Conversation, MessageSummary, ParsedMessage
from data_clients.whatsapp.reader import WhatsAppDBReader

__all__ = [
    "WhatsAppDBReader",
    "ParsedMessage",
    "Conversation",
    "MessageSummary",
]
