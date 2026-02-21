"""Abstract base class for embedding backends."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Abstract interface for text embedding."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single document text."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a search query (may use different input_type for retrieval)."""
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        ...
