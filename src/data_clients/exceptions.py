"""Unified exception hierarchy for data-clients."""


class DataClientError(Exception):
    """Base exception for all data-client errors."""


# Gmail
class GmailError(DataClientError):
    """Base exception for Gmail operations."""


class GmailAuthError(GmailError):
    """Gmail authentication or authorization failure."""


class GmailFetchError(GmailError):
    """Failed to fetch Gmail messages or data."""


# iMessage
class IMessageError(DataClientError):
    """Base exception for iMessage operations."""


class IMessageReadError(IMessageError):
    """Failed to read iMessage data."""


class IMessageSendError(IMessageError):
    """Failed to send iMessage."""


# Browser
class BrowserError(DataClientError):
    """Base exception for browser history operations."""


class BrowserHistoryReadError(BrowserError):
    """Failed to read browser history."""


# Contacts
class ContactsError(DataClientError):
    """Base exception for contacts operations."""


class ContactResolutionError(ContactsError):
    """Failed to resolve or look up a contact."""


# Calendar
class CalendarError(DataClientError):
    """Base exception for calendar operations."""


# Web
class WebFetchError(DataClientError):
    """Failed to fetch web content."""


class WebSearchError(DataClientError):
    """Failed to perform web search."""


# LLM
class LLMError(DataClientError):
    """Base exception for LLM client operations."""


# Embeddings
class EmbeddingError(DataClientError):
    """Base exception for embedding operations."""


# VectorStore
class VectorStoreError(DataClientError):
    """Base exception for vector store operations."""


# WhatsApp
class WhatsAppError(DataClientError):
    """Base exception for WhatsApp operations."""


class WhatsAppReadError(WhatsAppError):
    """Failed to read WhatsApp ChatStorage.sqlite."""


class WhatsAppAccountNotFoundError(WhatsAppError):
    """No WhatsApp account directories found on this machine."""
