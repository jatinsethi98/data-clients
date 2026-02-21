"""Abstract base class for vector store backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single search result from a vector store query."""

    doc_id: str
    score: float
    text: str | None
    metadata: dict


class BaseVectorStore(ABC):
    """Abstract interface for vector storage and retrieval."""

    @abstractmethod
    def add(self, doc_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        """Upsert a single document."""
        ...

    @abstractmethod
    def add_batch(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Upsert multiple documents."""
        ...

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """Similarity search returning ranked results."""
        ...

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Remove a document by ID."""
        ...

    @abstractmethod
    def delete_batch(self, doc_ids: list[str]) -> None:
        """Remove multiple documents by ID."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Total number of documents in the store."""
        ...
