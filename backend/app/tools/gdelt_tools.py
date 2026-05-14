import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial

from app.agents.state import SourceItem
from app.core.logging import get_logger

logger = get_logger(__name__)


def _gdelt_search_sync(query: str, max_results: int) -> list[SourceItem]:
    """Synchronous GDELT search — runs inside a thread pool."""
    try:
        from gdeltdoc import GdeltDoc, Filters

        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=1)

        f = Filters(
            keyword=query,
            startdate=start_dt.strftime("%Y-%m-%d"),
            enddate=end_dt.strftime("%Y-%m-%d"),
            language="English",
            timespan="1d",
        )

        gd = GdeltDoc()
        df = gd.article_search(f)

        if df is None or df.empty:
            return []

        items: list[SourceItem] = []
        for _, row in df.head(max_results).iterrows():
            title = str(row.get("title", "")).strip()
            url = str(row.get("url", "")).strip()
            domain = str(row.get("domain", "GDELT")).strip()
            seen_at = str(row.get("seendatetime", ""))

            if not url or not title:
                continue

            items.append({
                "url": url,
                "title": title,
                "source_name": domain or "GDELT",
                "published_at": seen_at,
                "raw_text": title[:2000],
                "feed_origin": "gdelt",
            })

        return items

    except ImportError:
        logger.warning("gdeltdoc_not_installed")
        return []
    except Exception as exc:
        logger.warning("gdelt_search_error", query=query, error=str(exc))
        return []


async def fetch_gdelt(query: str, max_results: int = 30) -> list[SourceItem]:
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(
        None,
        partial(_gdelt_search_sync, query, max_results),
    )
    logger.info("gdelt_fetched", query=query, count=len(items))
    return items
