"""Tests for browser history reader."""

from unittest.mock import patch
from pathlib import Path

import pytest

from data_clients.browser.reader import BrowserHistoryReader


def test_clamp_days():
    assert BrowserHistoryReader._clamp_days(0) == 1
    assert BrowserHistoryReader._clamp_days(15) == 15
    assert BrowserHistoryReader._clamp_days(60) == 30


def test_safari_ts_to_iso():
    # 2024-01-01 00:00:00 UTC in Safari timestamp
    safari_ts = 757382400.0  # seconds since 2001-01-01
    iso = BrowserHistoryReader._safari_ts_to_iso(safari_ts)
    assert iso != ""
    assert "2025" in iso or "2024" in iso or "2023" in iso  # reasonable date


def test_safari_ts_to_iso_none():
    assert BrowserHistoryReader._safari_ts_to_iso(None) == ""


def test_chrome_ts_to_iso_none():
    assert BrowserHistoryReader._chrome_ts_to_iso(None) == ""


@patch.object(BrowserHistoryReader, "_fetch_safari_visits", return_value=[])
@patch.object(BrowserHistoryReader, "_fetch_chrome_visits", return_value=[])
def test_fetch_visits_empty(mock_chrome, mock_safari):
    reader = BrowserHistoryReader()
    # No visits from either source, no errors = empty list
    visits = reader.fetch_visits()
    assert visits == []
