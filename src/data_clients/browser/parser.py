"""Parse raw browser history rows into normalized visit records."""

from __future__ import annotations

from urllib.parse import urlparse

from data_clients.browser.models import ParsedBrowserVisit


def parse_visit(
    raw: dict,
    excluded_domains: list[str] | None = None,
    max_url_length: int = 2000,
    max_title_length: int = 300,
) -> ParsedBrowserVisit | None:
    """Normalize one raw visit row; returns None for filtered/invalid rows."""
    url = (raw.get("url") or "").strip()
    if not url:
        return None
    if len(url) > max_url_length:
        url = url[:max_url_length]

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    domain = _normalize_domain(parsed.netloc)
    if not domain:
        return None

    if _is_excluded_domain(domain, excluded_domains or []):
        return None

    source_type = (raw.get("source_type") or "").strip().lower()
    profile = (raw.get("profile") or "Default").strip()
    source_visit_id = str(raw.get("source_visit_id") or "").strip()
    visited_at = (raw.get("visited_at") or "").strip()
    if not source_type or not source_visit_id or not visited_at:
        return None

    title = (raw.get("title") or "").strip()
    if len(title) > max_title_length:
        title = title[:max_title_length]

    visit_uid = f"{source_type}:{profile}:{source_visit_id}"
    visit_count = int(raw.get("visit_count") or 1)
    transition = str(raw.get("transition") or "")

    return ParsedBrowserVisit(
        visit_uid=visit_uid,
        source_type=source_type,
        profile=profile,
        source_visit_id=source_visit_id,
        url=url,
        title=title,
        domain=domain,
        visited_at=visited_at,
        visit_count=max(1, visit_count),
        transition=transition,
    )


def _normalize_domain(netloc: str) -> str:
    domain = (netloc or "").strip().lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _is_excluded_domain(domain: str, excluded_domains: list[str]) -> bool:
    for blocked in excluded_domains:
        b = blocked.strip().lower()
        if not b:
            continue
        if domain == b or domain.endswith(f".{b}"):
            return True
    return False
