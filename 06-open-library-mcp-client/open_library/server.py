"""FastMCP server: thin MCP wrapper around the Open Library Search API."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("open-library")

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
USER_AGENT = "training-mcps-06-open-library/0.1 (educational lab)"
DEFAULT_FIELDS = "key,title,author_name,first_publish_year,edition_count"


def _normalize_limit(limit: int) -> int:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return min(limit, 20)


def _docs_to_books(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    books: list[dict[str, Any]] = []
    for doc in docs:
        key = str(doc.get("key") or "").strip()
        title = str(doc.get("title") or "").strip()
        if not title:
            continue
        authors = doc.get("author_name") or []
        if not isinstance(authors, list):
            authors = [str(authors)]
        books.append(
            {
                "title": title,
                "authors": [str(name) for name in authors if name],
                "first_publish_year": doc.get("first_publish_year"),
                "edition_count": doc.get("edition_count"),
                "work_key": key,
                "open_library_url": (
                    f"https://openlibrary.org{key}" if key.startswith("/") else None
                ),
            }
        )
    return books


@mcp.tool()
async def search_books(query: str, limit: int = 5) -> dict:
    """Search Open Library for books matching a free-text query.

    Uses https://openlibrary.org/search.json. Returns a compact list of works
    (title, authors, year, work key). No API key required.
    """
    cleaned = query.strip()
    if not cleaned:
        raise ToolError("query must not be empty")

    try:
        capped = _normalize_limit(limit)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    logger.info("search_books query=%r limit=%s", cleaned, capped)
    params = {
        "q": cleaned,
        "limit": capped,
        "fields": DEFAULT_FIELDS,
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                OPEN_LIBRARY_SEARCH_URL,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise ToolError(f"Open Library request failed: {exc}") from exc
    except ValueError as exc:
        raise ToolError(f"Open Library returned invalid JSON: {exc}") from exc

    docs = payload.get("docs") or []
    if not isinstance(docs, list):
        raise ToolError("Unexpected Open Library response (docs is not a list)")

    books = _docs_to_books(docs)
    return {
        "query": cleaned,
        "num_found": payload.get("numFound", payload.get("num_found")),
        "returned": len(books),
        "books": books,
        "source": OPEN_LIBRARY_SEARCH_URL,
    }


@mcp.tool()
async def search_authors(name: str, limit: int = 5) -> dict:
    """Search Open Library for authors by name.

    Uses https://openlibrary.org/search/authors.json.
    """
    cleaned = name.strip()
    if not cleaned:
        raise ToolError("name must not be empty")

    try:
        capped = _normalize_limit(limit)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    logger.info("search_authors name=%r limit=%s", cleaned, capped)
    url = "https://openlibrary.org/search/authors.json"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params={"q": cleaned, "limit": capped},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise ToolError(f"Open Library authors request failed: {exc}") from exc
    except ValueError as exc:
        raise ToolError(f"Open Library returned invalid JSON: {exc}") from exc

    docs = payload.get("docs") or []
    if not isinstance(docs, list):
        raise ToolError("Unexpected Open Library response (docs is not a list)")

    authors: list[dict[str, Any]] = []
    for doc in docs[:capped]:
        key = str(doc.get("key") or "").strip()
        author_name = str(doc.get("name") or "").strip()
        if not author_name:
            continue
        authors.append(
            {
                "name": author_name,
                "key": key,
                "work_count": doc.get("work_count"),
                "top_work": doc.get("top_work"),
                "open_library_url": (
                    f"https://openlibrary.org/authors/{key}" if key else None
                ),
            }
        )

    return {
        "name": cleaned,
        "num_found": payload.get("numFound", payload.get("num_found")),
        "returned": len(authors),
        "authors": authors,
        "source": url,
    }


if __name__ == "__main__":
    mcp.run()
