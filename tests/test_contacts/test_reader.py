"""Tests for contacts reader."""

import pytest

from data_clients.contacts.reader import normalize_phone, normalize_email, Contact


def test_normalize_phone_us():
    assert normalize_phone("+1 (555) 123-4567") == "5551234567"


def test_normalize_phone_short():
    assert normalize_phone("1234") == "1234"


def test_normalize_phone_11_digit():
    assert normalize_phone("15551234567") == "5551234567"


def test_normalize_email():
    assert normalize_email("  User@Example.COM  ") == "user@example.com"


def test_contact_dataclass():
    c = Contact(
        identifier="abc-123",
        full_name="John Doe",
        first_name="John",
        last_name="Doe",
        phone_numbers=["+15551234567"],
        email_addresses=["john@example.com"],
    )
    assert c.full_name == "John Doe"
    assert c.source == "macos_contacts"
