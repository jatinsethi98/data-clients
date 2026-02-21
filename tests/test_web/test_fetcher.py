"""Tests for web fetcher."""

import pytest

from data_clients.web.fetcher import _validate_url, WebFetcher
from data_clients.exceptions import WebFetchError


def test_validate_url_valid():
    is_safe, error, ip = _validate_url("https://example.com")
    assert is_safe is True
    assert error is None


def test_validate_url_blocked_scheme():
    is_safe, error, _ = _validate_url("file:///etc/passwd")
    assert is_safe is False
    assert "Blocked URL scheme" in error


def test_validate_url_localhost():
    is_safe, error, _ = _validate_url("http://localhost:8080")
    assert is_safe is False
    assert "localhost" in error


def test_validate_url_no_hostname():
    is_safe, error, _ = _validate_url("http://")
    assert is_safe is False


def test_validate_url_private_ip():
    is_safe, error, _ = _validate_url("http://192.168.1.1")
    assert is_safe is False
    assert "private" in error.lower()
