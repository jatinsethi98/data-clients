"""Gmail API client — merged from Jarvis (primary) and PA (auth, parser).

Heavy imports are deferred. Use explicit imports:
    from data_clients.gmail.client import Gmail
    from data_clients.gmail.auth import AuthManager
    from data_clients.gmail.parser import parse_message
    etc.
"""

# Light imports only (no external deps)
from data_clients.gmail.label import Label
from data_clients.gmail import query
from data_clients.gmail import label
from data_clients.gmail.models import ParsedEmail, EmailSummary


def __getattr__(name):
    """Lazy imports for classes that require optional dependencies."""
    if name == "Gmail":
        from data_clients.gmail.client import Gmail
        return Gmail
    if name == "AuthManager":
        from data_clients.gmail.auth import AuthManager
        return AuthManager
    if name == "Message":
        from data_clients.gmail.message import Message
        return Message
    if name == "Attachment":
        from data_clients.gmail.attachment import Attachment
        return Attachment
    if name == "parse_message":
        from data_clients.gmail.parser import parse_message
        return parse_message
    if name == "fetch_messages":
        from data_clients.gmail.fetcher import fetch_messages
        return fetch_messages
    if name == "get_account_email":
        from data_clients.gmail.fetcher import get_account_email
        return get_account_email
    raise AttributeError(f"module 'data_clients.gmail' has no attribute {name!r}")


__all__ = [
    "Gmail",
    "AuthManager",
    "Message",
    "Attachment",
    "Label",
    "query",
    "label",
    "parse_message",
    "ParsedEmail",
    "EmailSummary",
    "fetch_messages",
    "get_account_email",
]
