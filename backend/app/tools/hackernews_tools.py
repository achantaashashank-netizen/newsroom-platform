import httpx

from app.agents.state import SourceItem
from app.core.logging import get_logger

logger = get_logger(__name__)

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


async def fetch_hackernews(query: str, max_results: int = 20) -> list[SourceItem]:
    """Fetch top Hacker News stories matching a query via the Algolia HN API."""
    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": min(max_results, 50),
        "numericFilters": "points>10",  # only stories with some traction
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(HN_SEARCH_URL, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

        hits = data.get("hits", [])
        items: list[SourceItem] = []

        for hit in hits:
            url = hit.get("url", "")
            title = hit.get("title", "").strip()

            if not url or not title:
                continue

            story_text = hit.get("story_text") or ""
            raw = f"{title} {story_text}".strip()[:2000]
            created_at = hit.get("created_at", "")

            items.append({
                "url": url,
                "title": title,
                "source_name": "Hacker News",
                "published_at": created_at,
                "raw_text": raw,
                "feed_origin": "hackernews",
            })

        logger.info("hackernews_fetched", query=query, count=len(items))
        return items

    except Exception as exc:
        logger.warning("hackernews_error", query=query, error=str(exc))
        return []
