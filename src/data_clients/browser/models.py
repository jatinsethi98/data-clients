"""Data models for the browser history module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedBrowserVisit:
    """A normalized browser history entry."""

    visit_uid: str
    source_type: str  # "safari" | "chrome"
    profile: str
    source_visit_id: str
    url: str
    title: str
    domain: str
    visited_at: str
    visit_count: int = 1
    transition: str = ""


@dataclass
class BrowserSummary:
    """A generated summary of browsing activity."""

    source_filter: str | None
    summary_type: str  # "daily"
    date_range_start: str
    date_range_end: str
    visit_count: int
    summary_text: str
    key_topics: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
