"""Brave Search API client with sync and async interfaces."""

from __future__ import annotations

import logging

from data_clients.exceptions import WebSearchError

logger = logging.getLogger(__name__)


class BraveSearchClient:
    """Brave Search API client.

    Args:
        api_key: Brave Search API subscription token.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise WebSearchError(
                "Brave Search API key is required. "
                "Pass it directly or set BRAVE_SEARCH_API_KEY in your environment."
            )
        try:
            import httpx  # noqa: F401
        except ImportError:
            raise ImportError(
                "httpx is required for BraveSearchClient. "
                "Install with: pip install data-clients[web]"
            )
        self.api_key = api_key

    async def search(self, query: str, num_results: int = 5) -> list[dict]:
        """Async web search via Brave Search API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": num_results},
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": self.api_key,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("web", {}).get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                })
            return results
        except Exception as e:
            raise WebSearchError(f"Web search failed: {e}") from e

    def search_sync(self, query: str, num_results: int = 5) -> list[dict]:
        """Synchronous web search via Brave Search API."""
        import httpx

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": num_results},
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": self.api_key,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("web", {}).get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                })
            return results
        except Exception as e:
            raise WebSearchError(f"Web search failed: {e}") from e
