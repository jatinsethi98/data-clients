"""ChromaDB vector store backend."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from data_clients.exceptions import VectorStoreError
from data_clients.vectorstore.base import BaseVectorStore, SearchResult

logger = logging.getLogger(__name__)

COLLECTION_NAME = "assistant"


class ChromaVectorStore(BaseVectorStore):
    """Persistent ChromaDB collection for semantic search."""

    def __init__(self, persist_dir: Path, collection_name: str = COLLECTION_NAME):
        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        try:
            import chromadb
        except ImportError:
            raise ImportError(
                "chromadb is required for ChromaVectorStore. "
                "Install with: pip install data-clients[vectorstore-chroma]"
            )
        try:
            self.client = chromadb.PersistentClient(path=str(persist_dir))
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize ChromaDB: {e}") from e

    def add(self, doc_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        self.collection.upsert(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def add_batch(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        batch_size = 5000
        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i : i + batch_size],
                documents=texts[i : i + batch_size],
                embeddings=embeddings[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }
        if filters:
            kwargs["where"] = filters

        try:
            raw = self.collection.query(**kwargs)
        except Exception as e:
            raise VectorStoreError(f"ChromaDB search failed: {e}") from e

        results: list[SearchResult] = []
        if raw["ids"] and raw["ids"][0]:
            ids = raw["ids"][0]
            distances = raw["distances"][0] if raw.get("distances") else [0.0] * len(ids)
            documents = raw["documents"][0] if raw.get("documents") else [None] * len(ids)
            metadatas = raw["metadatas"][0] if raw.get("metadatas") else [{}] * len(ids)

            for doc_id, dist, doc, meta in zip(ids, distances, documents, metadatas):
                results.append(SearchResult(
                    doc_id=doc_id,
                    score=1.0 - dist,  # ChromaDB returns distance; convert to similarity
                    text=doc,
                    metadata=meta or {},
                ))

        return results

    def delete(self, doc_id: str) -> None:
        self.collection.delete(ids=[doc_id])

    def delete_batch(self, doc_ids: list[str]) -> None:
        if doc_ids:
            self.collection.delete(ids=doc_ids)

    def count(self) -> int:
        return self.collection.count()

    def get(self, doc_id: str) -> dict | None:
        """Get a specific document by ID (ChromaDB-specific)."""
        result = self.collection.get(ids=[doc_id], include=["metadatas", "documents"])
        if result["ids"]:
            return {
                "id": result["ids"][0],
                "document": result["documents"][0] if result["documents"] else None,
                "metadata": result["metadatas"][0] if result["metadatas"] else None,
            }
        return None

    def prune(self, retention_thresholds: dict) -> int:
        """Remove expired documents based on search_weight thresholds (ChromaDB-specific).

        retention_thresholds: {
            "high":   {"min_weight": 0.8, "days": 365},
            "medium": {"min_weight": 0.4, "days": 90},
            "low":    {"min_weight": 0.0, "days": 30},
        }
        """
        total = self.count()
        if total == 0:
            return 0

        all_docs = self.collection.get(include=["metadatas"])
        ids_to_delete = []
        now = datetime.now()

        for doc_id, metadata in zip(all_docs["ids"], all_docs["metadatas"]):
            if not metadata:
                continue

            weight = metadata.get("search_weight", 0.0)
            date_str = metadata.get("date", "")

            if not date_str:
                continue

            try:
                doc_date = datetime.fromisoformat(date_str[:10])
            except (ValueError, TypeError):
                continue

            max_days = 30
            sorted_tiers = sorted(
                retention_thresholds.values(),
                key=lambda t: t["min_weight"],
                reverse=True,
            )
            for tier in sorted_tiers:
                if weight >= tier["min_weight"]:
                    max_days = tier["days"]
                    break

            override_days = metadata.get("retention_days")
            if override_days is not None:
                try:
                    max_days = min(max_days, int(override_days))
                except (TypeError, ValueError):
                    pass

            if (now - doc_date).days > max_days:
                ids_to_delete.append(doc_id)

        if ids_to_delete:
            self.delete_batch(ids_to_delete)
            logger.info(f"Pruned {len(ids_to_delete)} expired documents")

        return len(ids_to_delete)
