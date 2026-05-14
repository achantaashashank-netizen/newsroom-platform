import asyncio
from collections import Counter
from datetime import datetime, timezone

from app.agents.state import NewsroomState, SourceItem
from app.core.logging import get_logger
from app.tools.gdelt_tools import fetch_gdelt
from app.tools.hackernews_tools import fetch_hackernews
from app.tools.newsapi_tools import fetch_newsapi
from app.tools.rss_tools import fetch_all_rss

logger = get_logger(__name__)


async def discovery_node(state: NewsroomState) -> dict:
    run_id = state["run_id"]
    query = state["query"]

    logs = [{
        "node": "discovery_node",
        "type": "start",
        "message": f"Starting news discovery for: '{query}' — scanning RSS feeds, NewsAPI, GDELT, Hacker News",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]

    try:
        # Parallel fetch from all sources
        rss_results, newsapi_results, gdelt_results, hn_results = await asyncio.gather(
            fetch_all_rss(query),
            fetch_newsapi(query, max_results=50),
            fetch_gdelt(query, max_results=30),
            fetch_hackernews(query, max_results=20),
            return_exceptions=True,
        )

        all_sources: list[SourceItem] = []
        source_counts: dict[str, int] = {}

        for label, results in [
            ("RSS", rss_results),
            ("NewsAPI", newsapi_results),
            ("GDELT", gdelt_results),
            ("Hacker News", hn_results),
        ]:
            if isinstance(results, list):
                all_sources.extend(results)
                source_counts[label] = len(results)
                logs.append({
                    "node": "discovery_node",
                    "type": "progress",
                    "message": f"{label}: found {len(results)} articles",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                source_counts[label] = 0
                logger.warning("discovery_source_failed", source=label, error=str(results))

        # Deduplicate by URL
        seen: set[str] = set()
        unique_sources: list[SourceItem] = []
        for item in all_sources:
            if item["url"] and item["url"] not in seen:
                seen.add(item["url"])
                unique_sources.append(item)

        # Compute trending score: number of unique source names reporting this
        source_names = [s["source_name"] for s in unique_sources]
        name_counts = Counter(source_names)
        trending_score = min(len(name_counts) / 10.0, 1.0)  # normalize to 0-1

        discovery_metadata = {
            "rss_count": source_counts.get("RSS", 0),
            "newsapi_count": source_counts.get("NewsAPI", 0),
            "gdelt_count": source_counts.get("GDELT", 0),
            "hackernews_count": source_counts.get("Hacker News", 0),
            "total_unique": len(unique_sources),
            "unique_sources": len(name_counts),
            "source_breakdown": dict(name_counts.most_common(10)),
        }

        logs.append({
            "node": "discovery_node",
            "type": "done",
            "message": (
                f"Discovery complete — {len(unique_sources)} unique articles from "
                f"{len(name_counts)} sources "
                f"(RSS: {source_counts.get('RSS', 0)}, NewsAPI: {source_counts.get('NewsAPI', 0)}, "
                f"GDELT: {source_counts.get('GDELT', 0)}, HN: {source_counts.get('Hacker News', 0)}). "
                f"Trending score: {trending_score:.0%}"
            ),
            "progress": 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(
            "discovery_complete",
            run_id=run_id,
            total=len(unique_sources),
            sources=len(name_counts),
        )

        return {
            "raw_sources": unique_sources,
            "trending_score": trending_score,
            "discovery_metadata": discovery_metadata,
            "current_node": "discovery_node",
            "agent_logs": logs,
        }

    except Exception as exc:
        logger.exception("discovery_error", run_id=run_id, error=str(exc))
        logs.append({
            "node": "discovery_node",
            "type": "error",
            "message": f"Discovery failed: {exc}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "raw_sources": [],
            "trending_score": 0.0,
            "discovery_metadata": {},
            "error": str(exc),
            "current_node": "discovery_node",
            "agent_logs": logs,
        }
