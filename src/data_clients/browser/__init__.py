"""Browser history data access (Safari + Chrome, macOS)."""

from data_clients.browser.reader import BrowserHistoryReader
from data_clients.browser.parser import parse_visit
from data_clients.browser.models import ParsedBrowserVisit, BrowserSummary

__all__ = [
    "BrowserHistoryReader",
    "parse_visit",
    "ParsedBrowserVisit",
    "BrowserSummary",
]
