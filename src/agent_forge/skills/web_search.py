"""Web search skill — DuckDuckGo + SearxNG integration.

Search the internet for latest information without API key.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def web_search(
    query: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Perform web search and return structured results.

    Priority:
      1. DuckDuckGo HTML search (free, no API key)
      2. DuckDuckGo API fallback
      3. SearxNG (if SEARXNG_URL env var is set)

    Args:
        query: Search keywords.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with keys: title, snippet, url.
    """
    results = await _search_ddg_html(query, max_results)

    if not results:
        results = await _search_ddg_api(query, max_results)

    if not results:
        results = await _search_searxng(query, max_results)

    return results


async def _search_ddg_html(query: str, max_results: int) -> list[dict[str, Any]]:
    """DuckDuckGo HTML search (no API key)."""
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "AgentForge/1.0"},
            )
            resp.raise_for_status()
            return _parse_ddg_html(resp.text, max_results)
        except Exception as e:
            logger.warning("DuckDuckGo HTML search failed: %s", e)
            return []


def _parse_ddg_html(html: str, max_results: int) -> list[dict[str, Any]]:
    """Parse DuckDuckGo HTML results."""
    import re

    results: list[dict[str, Any]] = []
    for block in re.finditer(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]*)</a>', html):
        url = block.group(1)
        title = block.group(2).strip()
        snippet_match = re.search(
            re.escape(title) + r'.*?<a[^>]+class="result__snippet"[^>]*>([^<]*)</a>',
            html, re.DOTALL,
        )
        snippet = snippet_match.group(1).strip() if snippet_match else ""
        if title and url:
            results.append({"title": title, "snippet": snippet[:300], "url": url})
            if len(results) >= max_results:
                break
    return results


async def _search_ddg_api(query: str, max_results: int) -> list[dict[str, Any]]:
    """DuckDuckGo instant answer API fallback."""
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json"},
                headers={"User-Agent": "AgentForge/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("AbstractText"):
                return [{
                    "title": data.get("Heading", ""),
                    "snippet": data["AbstractText"][:300],
                    "url": data.get("FirstURL", ""),
                }]
            return []
        except Exception as e:
            logger.warning("DuckDuckGo API search failed: %s", e)
            return []


async def _search_searxng(query: str, max_results: int) -> list[dict[str, Any]]:
    """SearxNG open-source search engine (requires SEARXNG_URL env var)."""
    import os

    import httpx

    searx_url = os.getenv("SEARXNG_URL")
    if not searx_url:
        return []

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{searx_url}/search",
                params={"q": query, "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("content", "")[:300],
                    "url": r.get("url", ""),
                }
                for r in data.get("results", [])[:max_results]
            ]
        except Exception as e:
            logger.warning("SearxNG search failed: %s", e)
            return []
