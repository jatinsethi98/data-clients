"""SSRF-safe URL fetcher with sync and async interfaces."""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

from data_clients.exceptions import WebFetchError

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = {"http", "https"}

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _validate_url(url: str) -> tuple[bool, str | None, str | None]:
    """Validate a URL for safety. Returns (is_safe, error_message, resolved_ip)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format", None

    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False, f"Blocked URL scheme: {parsed.scheme}. Only http/https allowed.", None

    hostname = parsed.hostname
    if not hostname:
        return False, "URL has no hostname", None

    if hostname in ("localhost", "0.0.0.0"):
        return False, "Blocked: localhost access not allowed", None

    resolved_ip = None
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
        for addr_info in addr_infos:
            ip = ipaddress.ip_address(addr_info[4][0])
            for network in _BLOCKED_NETWORKS:
                if ip in network:
                    return False, f"Blocked: URL resolves to private/internal IP ({ip})", None
            if resolved_ip is None:
                resolved_ip = str(ip)
    except socket.gaierror:
        return False, f"Cannot resolve hostname: {hostname}", None

    return True, None, resolved_ip


class WebFetcher:
    """SSRF-safe URL fetcher with content extraction.

    Args:
        max_response_bytes: Maximum response size in bytes (default 1MB).
        max_redirects: Maximum number of redirects to follow (default 5).
    """

    def __init__(
        self,
        max_response_bytes: int = 1_048_576,
        max_redirects: int = 5,
    ):
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects

    async def fetch(
        self,
        url: str,
        extract_mode: str = "text",
        max_length: int = 5000,
    ) -> dict:
        """Async fetch and extract content from a URL.

        Args:
            url: The URL to fetch.
            extract_mode: 'text' (cleaned text), 'raw' (raw HTML), or 'links'.
            max_length: Maximum length of extracted content.

        Returns:
            Dict with url, content/links, status_code, content_type.
        """
        try:
            import httpx
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "httpx and beautifulsoup4 are required for WebFetcher. "
                "Install with: pip install data-clients[web]"
            )

        is_safe, error, resolved_ip = _validate_url(url)
        if not is_safe:
            raise WebFetchError(error)

        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=False,
                max_redirects=0,
            ) as client:
                current_url = url
                response = None
                for _ in range(self.max_redirects):
                    response = await client.get(
                        current_url,
                        headers={
                            "User-Agent": "DataClients/1.0",
                            "Host": urlparse(current_url).hostname or "",
                        },
                    )
                    if response.is_redirect and response.has_redirect_location:
                        redirect_url = (
                            str(response.next_request.url)
                            if response.next_request
                            else None
                        )
                        if redirect_url is None:
                            break
                        redir_safe, redir_err, _ = _validate_url(redirect_url)
                        if not redir_safe:
                            raise WebFetchError(f"Redirect blocked: {redir_err}")
                        current_url = redirect_url
                    else:
                        break

                if response is None:
                    raise WebFetchError("No response received")

                if len(response.content) > self.max_response_bytes:
                    raise WebFetchError(
                        f"Response too large (>{self.max_response_bytes} bytes)"
                    )

                response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            raw_text = response.text

            if extract_mode == "raw":
                return {
                    "url": str(response.url),
                    "content": raw_text[:max_length],
                    "content_length": len(raw_text[:max_length]),
                    "status_code": response.status_code,
                    "content_type": content_type,
                }
            elif extract_mode == "links":
                soup = BeautifulSoup(raw_text, "html.parser")
                links = []
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    text = a_tag.get_text(strip=True)
                    links.append({"href": href, "text": text[:100]})
                return {
                    "url": str(response.url),
                    "links": links[:100],
                    "count": len(links),
                    "status_code": response.status_code,
                }
            else:
                if "html" in content_type or raw_text.strip().startswith("<"):
                    soup = BeautifulSoup(raw_text, "html.parser")
                    for element in soup(
                        ["script", "style", "nav", "footer", "header"]
                    ):
                        element.decompose()
                    extracted = soup.get_text(separator="\n", strip=True)
                else:
                    extracted = raw_text
                extracted = extracted[:max_length]
                return {
                    "url": str(response.url),
                    "content": extracted,
                    "content_length": len(extracted),
                    "status_code": response.status_code,
                    "content_type": content_type,
                }
        except WebFetchError:
            raise
        except Exception as e:
            raise WebFetchError(f"Fetch failed: {e}") from e

    def fetch_sync(
        self,
        url: str,
        extract_mode: str = "text",
        max_length: int = 5000,
    ) -> dict:
        """Synchronous fetch and extract content from a URL."""
        try:
            import httpx
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "httpx and beautifulsoup4 are required for WebFetcher. "
                "Install with: pip install data-clients[web]"
            )

        is_safe, error, resolved_ip = _validate_url(url)
        if not is_safe:
            raise WebFetchError(error)

        try:
            with httpx.Client(
                timeout=10.0,
                follow_redirects=False,
                max_redirects=0,
            ) as client:
                current_url = url
                response = None
                for _ in range(self.max_redirects):
                    response = client.get(
                        current_url,
                        headers={
                            "User-Agent": "DataClients/1.0",
                            "Host": urlparse(current_url).hostname or "",
                        },
                    )
                    if response.is_redirect and response.has_redirect_location:
                        redirect_url = (
                            str(response.next_request.url)
                            if response.next_request
                            else None
                        )
                        if redirect_url is None:
                            break
                        redir_safe, redir_err, _ = _validate_url(redirect_url)
                        if not redir_safe:
                            raise WebFetchError(f"Redirect blocked: {redir_err}")
                        current_url = redirect_url
                    else:
                        break

                if response is None:
                    raise WebFetchError("No response received")

                if len(response.content) > self.max_response_bytes:
                    raise WebFetchError(
                        f"Response too large (>{self.max_response_bytes} bytes)"
                    )

                response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            raw_text = response.text

            if extract_mode == "raw":
                return {
                    "url": str(response.url),
                    "content": raw_text[:max_length],
                    "content_length": len(raw_text[:max_length]),
                    "status_code": response.status_code,
                    "content_type": content_type,
                }
            elif extract_mode == "links":
                soup = BeautifulSoup(raw_text, "html.parser")
                links = []
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    text = a_tag.get_text(strip=True)
                    links.append({"href": href, "text": text[:100]})
                return {
                    "url": str(response.url),
                    "links": links[:100],
                    "count": len(links),
                    "status_code": response.status_code,
                }
            else:
                if "html" in content_type or raw_text.strip().startswith("<"):
                    soup = BeautifulSoup(raw_text, "html.parser")
                    for element in soup(
                        ["script", "style", "nav", "footer", "header"]
                    ):
                        element.decompose()
                    extracted = soup.get_text(separator="\n", strip=True)
                else:
                    extracted = raw_text
                extracted = extracted[:max_length]
                return {
                    "url": str(response.url),
                    "content": extracted,
                    "content_length": len(extracted),
                    "status_code": response.status_code,
                    "content_type": content_type,
                }
        except WebFetchError:
            raise
        except Exception as e:
            raise WebFetchError(f"Fetch failed: {e}") from e
