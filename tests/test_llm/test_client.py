"""Tests for LLM client."""

import pytest

from data_clients.llm.client import LLMClient, AsyncLLMClient
from data_clients.exceptions import LLMError


def test_init_requires_api_key():
    with pytest.raises(LLMError, match="API key is required"):
        LLMClient(api_key="")


def test_async_init_requires_api_key():
    with pytest.raises(LLMError, match="API key is required"):
        AsyncLLMClient(api_key="")
