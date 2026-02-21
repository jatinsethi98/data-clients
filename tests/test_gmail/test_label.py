"""Tests for Gmail label."""

from data_clients.gmail.label import Label, INBOX, UNREAD


def test_label_equality_with_string():
    assert INBOX == "INBOX"
    assert UNREAD == "UNREAD"


def test_label_equality_with_label():
    other = Label("INBOX", "INBOX")
    assert INBOX == other


def test_label_inequality():
    assert INBOX != UNREAD


def test_label_hash():
    labels = {INBOX, UNREAD}
    assert INBOX in labels


def test_label_str():
    assert str(INBOX) == "INBOX"


def test_label_repr():
    assert "INBOX" in repr(INBOX)
