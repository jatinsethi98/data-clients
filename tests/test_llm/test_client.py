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


def test_init_accepts_none_api_key_with_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    client = LLMClient(api_key=None)
    assert client.model == "claude-haiku-4-5-20251001"

def test_init_accepts_none_api_key_without_env_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMError, match="API key is required"):
        LLMClient(api_key=None)

def test_async_init_accepts_none_api_key_with_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    client = AsyncLLMClient(api_key=None)
    assert client.model == "claude-haiku-4-5-20251001"

def test_client_property():
    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    client = LLMClient()
    assert client.client is client._client
