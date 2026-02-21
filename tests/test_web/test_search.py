"""Tests for Brave Search client."""

import pytest

from data_clients.web.search import BraveSearchClient
from data_clients.exceptions import WebSearchError


def test_init_requires_api_key():
    with pytest.raises(WebSearchError, match="API key is required"):
        BraveSearchClient(api_key="")


def test_init_succeeds():
    client = BraveSearchClient(api_key="test-key")
    assert client.api_key == "test-key"
