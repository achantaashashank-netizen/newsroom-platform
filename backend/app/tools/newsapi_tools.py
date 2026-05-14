import httpx

from app.agents.state import SourceItem
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2"


async def fetch_newsapi(query: str, max_results: int = 30) -> list[SourceItem]:
    if not settings.NEWSAPI_KEY:
        logger.warning("newsapi_key_missing")
        return []

    params = {
        "q": query,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": min(max_results, 100),
        "apiKey": settings.NEWSAPI_KEY,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{NEWSAPI_BASE}/everything", params=params, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

            # Developer plan returns error in status field, not HTTP error
            if data.get("status") != "ok":
                logger.warning("newsapi_error_response", message=data.get("message"))
                return []

        articles = data.get("articles", [])
        items: list[SourceItem] = []

        for article in articles:
            source = article.get("source", {})
            items.append({
                "url": article.get("url", ""),
                "title": article.get("title", ""),
                "source_name": source.get("name", "Unknown"),
                "published_at": article.get("publishedAt", ""),
                "raw_text": f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".strip()[:2000],
                "feed_origin": "newsapi",
            })

        logger.info("newsapi_fetched", query=query, count=len(items))
        return items

    except Exception as exc:
        logger.warning("newsapi_error", query=query, error=str(exc))
        return []
