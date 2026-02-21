"""Tests for exception hierarchy."""

from data_clients.exceptions import (
    DataClientError,
    GmailError,
    GmailAuthError,
    GmailFetchError,
    IMessageError,
    IMessageReadError,
    IMessageSendError,
    BrowserError,
    BrowserHistoryReadError,
    ContactsError,
    ContactResolutionError,
    CalendarError,
    WebFetchError,
    WebSearchError,
    LLMError,
    EmbeddingError,
    VectorStoreError,
)


def test_all_inherit_from_base():
    for exc_class in [
        GmailError, GmailAuthError, GmailFetchError,
        IMessageError, IMessageReadError, IMessageSendError,
        BrowserError, BrowserHistoryReadError,
        ContactsError, ContactResolutionError,
        CalendarError,
        WebFetchError, WebSearchError,
        LLMError,
        EmbeddingError,
        VectorStoreError,
    ]:
        assert issubclass(exc_class, DataClientError)


def test_gmail_hierarchy():
    assert issubclass(GmailAuthError, GmailError)
    assert issubclass(GmailFetchError, GmailError)


def test_imessage_hierarchy():
    assert issubclass(IMessageReadError, IMessageError)
    assert issubclass(IMessageSendError, IMessageError)


def test_exception_message():
    e = GmailAuthError("test error")
    assert str(e) == "test error"
