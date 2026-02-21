"""Voyage AI embedding backend."""

from __future__ import annotations

import logging
import time

from data_clients.embeddings.base import BaseEmbedder
from data_clients.exceptions import EmbeddingError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class VoyageEmbedder(BaseEmbedder):
    """Voyage AI embeddings with retry logic."""

    def __init__(self, api_key: str, model: str = "voyage-3-lite"):
        if not api_key:
            raise EmbeddingError(
                "Voyage API key is required. "
                "Pass it directly or set VOYAGE_API_KEY in your environment."
            )
        try:
            import voyageai
        except ImportError:
            raise ImportError(
                "voyageai is required for VoyageEmbedder. "
                "Install with: pip install data-clients[embeddings]"
            )
        self.client = voyageai.Client(api_key=api_key)
        self.model = model

    def _call_with_retry(self, texts: list[str], input_type: str) -> list[list[float]]:
        """Call Voyage API with exponential backoff on rate limit errors."""
        for attempt in range(MAX_RETRIES):
            try:
                result = self.client.embed(texts, model=self.model, input_type=input_type)
                return result.embeddings
            except Exception as e:
                err_str = str(e).lower()
                if "rate limit" in err_str or "429" in err_str or "reduced rate" in err_str:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                else:
                    raise
        # Final attempt without catching
        result = self.client.embed(texts, model=self.model, input_type=input_type)
        return result.embeddings

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        try:
            return self._call_with_retry([text], "document")[0]
        except Exception as e:
            raise EmbeddingError(f"Voyage embedding failed: {e}") from e

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query (uses query input_type for better retrieval)."""
        try:
            return self._call_with_retry([text], "query")[0]
        except Exception as e:
            raise EmbeddingError(f"Voyage query embedding failed: {e}") from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in batches (max 128 per call)."""
        all_embeddings: list[list[float]] = []
        batch_size = 128

        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            try:
                embeddings = self._call_with_retry(chunk, "document")
                all_embeddings.extend(embeddings)
            except Exception as e:
                raise EmbeddingError(
                    f"Voyage batch embedding failed at offset {i}: {e}"
                ) from e

        return all_embeddings
