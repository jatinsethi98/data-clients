"""Tests for browser history parser."""

from data_clients.browser.parser import parse_visit
from data_clients.browser.models import ParsedBrowserVisit


def test_parse_valid_visit():
    raw = {
        "source_type": "safari",
        "profile": "Default",
        "source_visit_id": "123",
        "url": "https://example.com/page",
        "title": "Example Page",
        "visit_count": 3,
        "transition": "",
        "visited_at": "2024-01-01T12:00:00",
    }
    result = parse_visit(raw)
    assert result is not None
    assert isinstance(result, ParsedBrowserVisit)
    assert result.domain == "example.com"
    assert result.visit_count == 3
    assert result.visit_uid == "safari:Default:123"


def test_parse_filters_non_http():
    raw = {
        "source_type": "safari",
        "source_visit_id": "1",
        "url": "file:///Users/test/file.html",
        "visited_at": "2024-01-01T12:00:00",
    }
    assert parse_visit(raw) is None


def test_parse_filters_excluded_domain():
    raw = {
        "source_type": "chrome",
        "profile": "Default",
        "source_visit_id": "1",
        "url": "https://ads.example.com/track",
        "title": "Ad",
        "visited_at": "2024-01-01T12:00:00",
    }
    result = parse_visit(raw, excluded_domains=["ads.example.com"])
    assert result is None


def test_parse_strips_www():
    raw = {
        "source_type": "chrome",
        "profile": "Default",
        "source_visit_id": "1",
        "url": "https://www.example.com/",
        "title": "Example",
        "visited_at": "2024-01-01T12:00:00",
    }
    result = parse_visit(raw)
    assert result is not None
    assert result.domain == "example.com"


def test_parse_empty_url():
    raw = {"url": "", "source_type": "chrome", "source_visit_id": "1", "visited_at": "2024-01-01"}
    assert parse_visit(raw) is None
