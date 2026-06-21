"""Web search tool API route.

Provides the web search endpoint for agents to call.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from agent_forge.models import User
from agent_forge.skills.web_search import web_search
from middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 5


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str


class WebSearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


@router.post("/tools/web-search", response_model=WebSearchResponse, tags=["tools"])
async def search_web(
    body: WebSearchRequest,
    _: User = Depends(get_current_user),
) -> dict:
    """
    Web search tool endpoint.

    Use this when you need to find the latest information, verify facts,
    or retrieve specific content from the internet.

    Supports DuckDuckGo (free) and SearxNG (requires SEARXNG_URL env var).

    Args:
        query: Search keywords.
        max_results: Number of results to return (default 5).
    """
    try:
        results = await web_search(body.query, body.max_results)
        search_results = [
            SearchResult(
                title=r.get("title", ""),
                snippet=r.get("snippet", ""),
                url=r.get("url", ""),
            )
            for r in results
        ]
        return {
            "query": body.query,
            "results": search_results,
            "total": len(results),
        }
    except Exception as e:
        logger.error("Web search failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}") from e


@router.get("/tools/web-search/suggest", tags=["tools"])
async def suggest_search_query(
    prefix: str = Query(..., min_length=1),
    _: User = Depends(get_current_user),
) -> dict:
    """Search autocomplete suggestions (DuckDuckGo)."""
    import httpx

    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(
                "https://duckduckgo.com/ac/",
                params={"q": prefix, "type": "list"},
            )
            resp.raise_for_status()
            data = resp.json()
            suggestions = data.get("query", "") or data.get("suggestions", [])
            return {
                "prefix": prefix,
                "suggestions": [s["phrase"] for s in suggestions[:5]],
            }
        except Exception as e:
            logger.warning("Search suggest failed: %s", e)
            return {"prefix": prefix, "suggestions": []}
