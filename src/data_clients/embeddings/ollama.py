"""Ollama embedding backend."""

from __future__ import annotations

import logging
import time

from data_clients.embeddings.base import BaseEmbedder
from data_clients.exceptions import EmbeddingError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class OllamaEmbedder(BaseEmbedder):
    """Ollama local embeddings with retry logic."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        try:
            import httpx  # noqa: F401
        except ImportError:
            raise ImportError(
                "httpx is required for OllamaEmbedder. "
                "Install with: pip install data-clients[embeddings]"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _call_api(self, text: str) -> list[float]:
        """Call Ollama embeddings API with retry."""
        import httpx

        for attempt in range(MAX_RETRIES):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model, "prompt": text},
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["embedding"]
            except Exception as e:
                err_str = str(e).lower()
                if "connection" in err_str or "timeout" in err_str:
                    wait = 2 ** attempt
                    logger.warning(f"Ollama connection issue, retrying in {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                else:
                    raise EmbeddingError(f"Ollama embedding failed: {e}") from e
        raise EmbeddingError(f"Ollama embedding failed after {MAX_RETRIES} retries")

    def embed(self, text: str) -> list[float]:
        return self._call_api(text)

    def embed_query(self, text: str) -> list[float]:
        return self._call_api(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Ollama doesn't support batch, call one at a time
        return [self._call_api(text) for text in texts]
