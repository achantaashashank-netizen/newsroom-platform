import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from app.workers.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.workers.tasks.discovery_tasks.periodic_discovery_task")
def periodic_discovery_task():
    """Auto-discover top 3 trending topics and run the full pipeline for each. Fires every 30 min."""
    try:
        asyncio.run(_async_discover())
    except Exception as exc:
        logger.exception("periodic_discovery_error", error=str(exc))


async def _async_discover() -> None:
    import redis.asyncio as aioredis
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.config import settings
    from app.models.story import Story
    from app.agents.coordinator import run_graph
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    redis_client = aioredis.from_url(settings.REDIS_URL)
    try:
        topics = await _fetch_top_topics()
        if not topics:
            logger.info("periodic_discovery_no_topics")
            return

        logger.info("periodic_discovery_topics_found", count=len(topics))

        async with AsyncPostgresSaver.from_conn_string(
            settings.DATABASE_URL_SYNC.replace("postgresql+psycopg2", "postgresql")
        ) as checkpointer:
            await checkpointer.setup()

            for topic in topics[:3]:
                async with AsyncSessionLocal() as db:
                    # Skip if a story for this keyword was already created in the last 2 hours
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
                    result = await db.execute(
                        select(Story).where(
                            Story.query.ilike(f"%{topic['keyword']}%"),
                            Story.created_at >= cutoff,
                            Story.status.notin_(["failed", "rejected"]),
                        ).limit(1)
                    )
                    if result.scalar_one_or_none():
                        logger.info("periodic_discovery_skipped", keyword=topic["keyword"], reason="recent_run_exists")
                        continue

                    run_id = str(uuid.uuid4())
                    logger.info("periodic_discovery_starting", keyword=topic["keyword"], run_id=run_id)

                    try:
                        await run_graph(
                            run_id=run_id,
                            query=topic["query"],
                            triggered_by="scheduler",
                            redis=redis_client,
                            db=db,
                            checkpointer=checkpointer,
                            user_id=None,
                        )
                        await db.commit()
                        logger.info("periodic_discovery_done", run_id=run_id)
                    except Exception as exc:
                        logger.exception("periodic_discovery_run_error", run_id=run_id, error=str(exc))
    finally:
        await redis_client.aclose()


async def _fetch_top_topics() -> list[dict]:
    """Fetch all RSS feeds in parallel and extract the top trending topics by cross-source mention frequency."""
    import re
    import httpx
    import feedparser
    from collections import defaultdict
    from app.tools.rss_tools import RSS_FEEDS

    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "are", "was", "were", "be", "been", "have", "has",
        "had", "do", "does", "did", "will", "would", "could", "should", "may",
        "might", "this", "that", "these", "those", "its", "it", "he", "she",
        "they", "we", "you", "i", "his", "her", "their", "our", "as", "by",
        "from", "up", "about", "into", "through", "after", "over", "says",
        "said", "new", "also", "more", "than", "can", "not", "no", "how",
        "what", "when", "who", "all", "before", "during", "amid",
    }

    async def _fetch(client: httpx.AsyncClient, name: str, url: str) -> list[dict]:
        try:
            r = await client.get(url, timeout=8.0, follow_redirects=True)
            feed = feedparser.parse(r.text)
            return [
                {"title": e.get("title", "").strip(), "source": name}
                for e in feed.entries[:15]
                if e.get("title", "").strip()
            ]
        except Exception:
            return []

    async with httpx.AsyncClient(headers={"User-Agent": "NewsroomBot/1.0"}) as client:
        results = await asyncio.gather(*[_fetch(client, n, u) for n, u in RSS_FEEDS])

    all_articles = [item for batch in results for item in batch]
    if not all_articles:
        return []

    def extract_keywords(title: str) -> list[str]:
        words = re.findall(r"[A-Za-z][a-z]{2,}", title)
        return [w.lower() for w in words if w.lower() not in STOP_WORDS and len(w) > 3]

    keyword_articles: dict[str, list[dict]] = defaultdict(list)
    for article in all_articles:
        for kw in extract_keywords(article["title"]):
            keyword_articles[kw].append(article)

    topics: dict[str, dict] = {}
    for kw, arts in keyword_articles.items():
        sources = list({a["source"] for a in arts})
        if len(sources) < 2:
            continue
        best = max(arts, key=lambda a: len(extract_keywords(a["title"])))
        topics[kw] = {
            "keyword": kw,
            "query": best["title"],
            "source_count": len(sources),
            "trending_score": round(len(arts) / len(all_articles) * 100, 2),
        }

    return sorted(topics.values(), key=lambda t: t["source_count"], reverse=True)
