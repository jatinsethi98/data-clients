"""Qdrant vector store backend."""

from __future__ import annotations

import logging

from data_clients.exceptions import VectorStoreError
from data_clients.vectorstore.base import AsyncBaseVectorStore, BaseVectorStore, SearchResult

logger = logging.getLogger(__name__)


class QdrantVectorStore(BaseVectorStore):
    """Qdrant vector store with sync client."""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "default",
        vector_size: int = 768,
    ):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError:
            raise ImportError(
                "qdrant-client is required for QdrantVectorStore. "
                "Install with: pip install data-clients[vectorstore-qdrant]"
            )
        self.collection_name = collection_name
        try:
            self.client = QdrantClient(url=url)
            # Ensure collection exists
            collections = [c.name for c in self.client.get_collections().collections]
            if collection_name not in collections:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize Qdrant: {e}") from e

    def add(self, doc_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        from qdrant_client.models import PointStruct

        payload = {**metadata, "_text": text}
        point = PointStruct(id=doc_id, vector=embedding, payload=payload)
        try:
            self.client.upsert(collection_name=self.collection_name, points=[point])
        except Exception as e:
            raise VectorStoreError(f"Qdrant upsert failed: {e}") from e

    def add_batch(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        from qdrant_client.models import PointStruct

        batch_size = 100
        for i in range(0, len(ids), batch_size):
            points = []
            for j in range(i, min(i + batch_size, len(ids))):
                payload = {**metadatas[j], "_text": texts[j]}
                points.append(PointStruct(id=ids[j], vector=embeddings[j], payload=payload))
            try:
                self.client.upsert(collection_name=self.collection_name, points=points)
            except Exception as e:
                raise VectorStoreError(f"Qdrant batch upsert failed: {e}") from e

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            qdrant_filter = Filter(must=conditions)

        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=n_results,
                query_filter=qdrant_filter,
            )
        except Exception as e:
            raise VectorStoreError(f"Qdrant search failed: {e}") from e

        results: list[SearchResult] = []
        for hit in hits:
            payload = hit.payload or {}
            text = payload.get("_text")
            metadata = {k: v for k, v in payload.items() if k != "_text"}
            results.append(SearchResult(
                doc_id=str(hit.id),
                score=hit.score,
                text=text,
                metadata=metadata,
            ))

        return results

    def delete(self, doc_id: str) -> None:
        from qdrant_client.models import PointIdsList

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=[doc_id]),
            )
        except Exception as e:
            raise VectorStoreError(f"Qdrant delete failed: {e}") from e

    def delete_batch(self, doc_ids: list[str]) -> None:
        if not doc_ids:
            return
        from qdrant_client.models import PointIdsList

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=doc_ids),
            )
        except Exception as e:
            raise VectorStoreError(f"Qdrant batch delete failed: {e}") from e

    def count(self) -> int:
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count
        except Exception as e:
            raise VectorStoreError(f"Qdrant count failed: {e}") from e


class AsyncQdrantVectorStore(AsyncBaseVectorStore):
    """Async Qdrant vector store using AsyncQdrantClient.

    Use the async factory to create: ``store = await AsyncQdrantVectorStore.create(url, ...)``
    """

    def __init__(self):
        raise TypeError(
            "Use 'await AsyncQdrantVectorStore.create(...)' instead of direct instantiation."
        )

    @classmethod
    async def create(
        cls,
        url: str = "http://localhost:6333",
        collection_name: str = "default",
        vector_size: int = 768,
    ) -> "AsyncQdrantVectorStore":
        """Async factory for creating an AsyncQdrantVectorStore."""
        try:
            from qdrant_client import AsyncQdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError:
            raise ImportError(
                "qdrant-client is required for AsyncQdrantVectorStore. "
                "Install with: pip install data-clients[vectorstore-qdrant]"
            )
        instance = object.__new__(cls)
        instance.collection_name = collection_name
        try:
            instance.client = AsyncQdrantClient(url=url)
            collections = [c.name for c in (await instance.client.get_collections()).collections]
            if collection_name not in collections:
                await instance.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize async Qdrant: {e}") from e
        return instance

    async def add(self, doc_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        from qdrant_client.models import PointStruct

        payload = {**metadata, "_text": text}
        point = PointStruct(id=doc_id, vector=embedding, payload=payload)
        try:
            await self.client.upsert(collection_name=self.collection_name, points=[point])
        except Exception as e:
            raise VectorStoreError(f"Async Qdrant upsert failed: {e}") from e

    async def add_batch(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        from qdrant_client.models import PointStruct

        batch_size = 100
        for i in range(0, len(ids), batch_size):
            points = []
            for j in range(i, min(i + batch_size, len(ids))):
                payload = {**metadatas[j], "_text": texts[j]}
                points.append(PointStruct(id=ids[j], vector=embeddings[j], payload=payload))
            try:
                await self.client.upsert(collection_name=self.collection_name, points=points)
            except Exception as e:
                raise VectorStoreError(f"Async Qdrant batch upsert failed: {e}") from e

    async def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            qdrant_filter = Filter(must=conditions)

        try:
            results = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=n_results,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            points = results.points
        except Exception as e:
            raise VectorStoreError(f"Async Qdrant search failed: {e}") from e

        search_results: list[SearchResult] = []
        for hit in points:
            payload = hit.payload or {}
            text = payload.get("_text")
            metadata = {k: v for k, v in payload.items() if k != "_text"}
            search_results.append(SearchResult(
                doc_id=str(hit.id),
                score=hit.score,
                text=text,
                metadata=metadata,
            ))
        return search_results

    async def delete(self, doc_id: str) -> None:
        from qdrant_client.models import PointIdsList

        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=[doc_id]),
            )
        except Exception as e:
            raise VectorStoreError(f"Async Qdrant delete failed: {e}") from e

    async def delete_batch(self, doc_ids: list[str]) -> None:
        if not doc_ids:
            return
        from qdrant_client.models import PointIdsList

        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=doc_ids),
            )
        except Exception as e:
            raise VectorStoreError(f"Async Qdrant batch delete failed: {e}") from e

    async def count(self) -> int:
        try:
            info = await self.client.get_collection(self.collection_name)
            return info.points_count
        except Exception as e:
            raise VectorStoreError(f"Async Qdrant count failed: {e}") from e

    async def close(self) -> None:
        """Close the async client connection."""
        await self.client.close()
