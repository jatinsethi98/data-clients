"""OpenAI embedding backend."""

from __future__ import annotations

import logging
import time

from data_clients.embeddings.base import BaseEmbedder
from data_clients.exceptions import EmbeddingError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embeddings API with retry logic."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        if not api_key:
            raise EmbeddingError(
                "OpenAI API key is required. "
                "Pass it directly or set OPENAI_API_KEY in your environment."
            )
        try:
            import httpx  # noqa: F401
        except ImportError:
            raise ImportError(
                "httpx is required for OpenAIEmbedder. "
                "Install with: pip install data-clients[embeddings]"
            )
        self.api_key = api_key
        self.model = model

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embeddings API with retry."""
        import httpx

        for attempt in range(MAX_RETRIES):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        "https://api.openai.com/v1/embeddings",
                        json={"input": texts, "model": self.model},
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    # Sort by index to maintain order
                    sorted_data = sorted(data["data"], key=lambda x: x["index"])
                    return [item["embedding"] for item in sorted_data]
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate" in err_str:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                else:
                    raise EmbeddingError(f"OpenAI embedding failed: {e}") from e
        raise EmbeddingError(f"OpenAI embedding failed after {MAX_RETRIES} retries")

    def embed(self, text: str) -> list[float]:
        return self._call_api([text])[0]

    def embed_query(self, text: str) -> list[float]:
        return self._call_api([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        batch_size = 100  # OpenAI supports up to 2048 but 100 is safe

        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            embeddings = self._call_api(chunk)
            all_embeddings.extend(embeddings)

        return all_embeddings
