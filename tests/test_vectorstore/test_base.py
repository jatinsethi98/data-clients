"""Tests for vector store base class."""

import pytest

from data_clients.vectorstore.base import BaseVectorStore, SearchResult


def test_base_vectorstore_is_abstract():
    with pytest.raises(TypeError):
        BaseVectorStore()


def test_async_base_vectorstore_is_abstract():
    from data_clients.vectorstore.base import AsyncBaseVectorStore
    with pytest.raises(TypeError):
        AsyncBaseVectorStore()


def test_search_result_dataclass():
    result = SearchResult(
        doc_id="doc1",
        score=0.95,
        text="Hello world",
        metadata={"source": "test"},
    )
    assert result.doc_id == "doc1"
    assert result.score == 0.95
    assert result.text == "Hello world"
