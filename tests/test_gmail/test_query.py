"""Tests for Gmail query builder."""

from data_clients.gmail.query import construct_query


def test_simple_sender():
    q = construct_query(sender="alice@example.com")
    assert q == "from:alice@example.com"


def test_and_terms():
    q = construct_query(sender="alice@example.com", subject="Meeting")
    assert "from:alice@example.com" in q
    assert "subject:Meeting" in q


def test_or_senders():
    q = construct_query(sender=["alice@example.com", "bob@example.com"])
    assert "{" in q  # OR grouping
    assert "from:alice@example.com" in q
    assert "from:bob@example.com" in q


def test_exclude():
    q = construct_query(exclude_sender="spam@example.com")
    assert "-from:spam@example.com" in q


def test_newer_than():
    q = construct_query(newer_than=(5, "day"))
    assert q == "newer_than:5d"


def test_starred():
    q = construct_query(starred=True)
    assert q == "is:starred"


def test_labels():
    q = construct_query(labels=["Work", "Important"])
    assert "label:Work" in q
    assert "label:Important" in q
