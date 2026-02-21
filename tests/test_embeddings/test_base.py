"""Tests for embedding base class."""

import pytest

from data_clients.embeddings.base import BaseEmbedder


def test_base_embedder_is_abstract():
    with pytest.raises(TypeError):
        BaseEmbedder()
