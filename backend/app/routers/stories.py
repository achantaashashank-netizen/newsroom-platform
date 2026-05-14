import asyncio
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.redis import get_redis_dep
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.story import (
    ApproveRequest,
    EditRequest,
    PublishRequest,
    RejectRequest,
    RunStoryRequest,
    RunStoryResponse,
    StoryRead,
)
from app.services.story_service import StoryService

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("/trending")
async def get_trending_topics(current_user: User = Depends(get_current_user)):
    """Fetch top 20 trending topics from RSS feeds without running the full pipeline."""
    import asyncio
    import httpx
    import feedparser
    import re
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
        "what", "when", "who", "all", "after", "before", "during", "amid",
    }

    async def _fetch_feed(client: httpx.AsyncClient, name: str, url: str):
        try:
            r = await client.get(url, timeout=8.0, follow_redirects=True)
            feed = feedparser.parse(r.text)
            items = []
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", ""))[:300]
                if title:
                    items.append({"title": title, "summary": summary, "source": name})
            return items
        except Exception:
            return []

    async with httpx.AsyncClient(headers={"User-Agent": "NewsroomBot/1.0"}) as client:
        results = await asyncio.gather(*[_fetch_feed(client, n, u) for n, u in RSS_FEEDS])

    all_articles = [item for batch in results for item in batch]

    # Extract significant words from each headline
    def extract_keywords(title: str) -> list[str]:
        words = re.findall(r"[A-Za-z][a-z]{2,}", title)
        return [w.lower() for w in words if w.lower() not in STOP_WORDS and len(w) > 3]

    # Build keyword → articles index
    keyword_articles: dict[str, list[dict]] = defaultdict(list)
    for article in all_articles:
        for kw in extract_keywords(article["title"]):
            keyword_articles[kw].append(article)

    # Find clusters: pairs of keywords that co-occur across multiple sources
    # Score = unique sources that mention these keywords
    topic_clusters: dict[str, dict] = {}
    for kw, arts in keyword_articles.items():
        if len(arts) < 2:
            continue
        sources = list({a["source"] for a in arts})
        if len(sources) < 2:
            continue
        # Use the most common/longest title mentioning this keyword as the topic label
        best = max(arts, key=lambda a: len(extract_keywords(a["title"])))
        cluster_key = kw
        if cluster_key not in topic_clusters or len(sources) > len(topic_clusters[cluster_key]["sources"]):
            topic_clusters[cluster_key] = {
                "keyword": kw,
                "query": best["title"],
                "headline": best["title"],
                "summary": best["summary"],
                "source_count": len(sources),
                "sources": sources[:5],
                "trending_score": round(len(arts) / len(all_articles) * 100, 1),
            }

    # Sort by source count desc, deduplicate by similar headlines
    sorted_topics = sorted(topic_clusters.values(), key=lambda t: t["source_count"], reverse=True)

    # Deduplicate: skip if headline is too similar to an already-included topic
    seen_words: list[set] = []
    unique_topics = []
    for topic in sorted_topics:
        words = set(extract_keywords(topic["headline"]))
        if any(len(words & seen) / max(len(words | seen), 1) > 0.6 for seen in seen_words):
            continue
        seen_words.append(words)
        unique_topics.append(topic)
        if len(unique_topics) == 20:
            break

    return unique_topics


@router.post("/run", response_model=RunStoryResponse, status_code=201)
async def run_story(
    body: RunStoryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    from app.agents.coordinator import run_graph

    run_id = str(uuid.uuid4())

    story_service = StoryService(db)
    story = await story_service.create_story(
        run_id=run_id,
        query=body.query,
        triggered_by=body.triggered_by,
        created_by_user_id=current_user.id,
    )
    await db.commit()

    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.agents.coordinator import run_graph
        from app.agents.graph import get_graph
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from app.core.config import settings

        async with AsyncSessionLocal() as background_db:
            async with AsyncPostgresSaver.from_conn_string(
                settings.DATABASE_URL_SYNC.replace("postgresql+psycopg2", "postgresql")
            ) as checkpointer:
                await checkpointer.setup()
                await run_graph(
                    run_id=run_id,
                    story_id=story.id,
                    query=body.query,
                    triggered_by=body.triggered_by,
                    redis=redis,
                    db=background_db,
                    checkpointer=checkpointer,
                    user_id=current_user.id,
                )
                await background_db.commit()

    background_tasks.add_task(_run)

    return RunStoryResponse(run_id=run_id, story_id=story.id)


@router.get("", response_model=list[StoryRead])
async def list_stories(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StoryService(db)
    return await service.list_stories(limit=limit, offset=offset)


@router.get("/run/{run_id}", response_model=StoryRead)
async def get_story_by_run_id(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StoryService(db)
    story = await service.get_by_run_id(run_id)
    if not story:
        raise NotFoundError("Story")
    return story


@router.get("/{story_id}", response_model=StoryRead)
async def get_story(
    story_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StoryService(db)
    story = await service.get_by_id(story_id)
    if not story:
        raise NotFoundError("Story")
    return story


@router.post("/{run_id}/approve")
async def approve_story(
    run_id: str,
    body: ApproveRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    service = StoryService(db)
    story = await service.get_by_run_id(run_id)
    if not story:
        raise NotFoundError("Story")

    await service.approve_story(story.id, user_id=current_user.id, notes=body.notes)
    await db.commit()

    async def _resume():
        from app.core.database import AsyncSessionLocal
        from app.agents.coordinator import resume_graph
        from app.agents.graph import get_graph
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from app.core.config import settings
        from langchain_core.runnables import RunnableConfig

        async with AsyncSessionLocal() as bg_db:
            async with AsyncPostgresSaver.from_conn_string(
                settings.DATABASE_URL_SYNC.replace("postgresql+psycopg2", "postgresql")
            ) as checkpointer:
                await checkpointer.setup()
                graph = get_graph(checkpointer=checkpointer)

                # Update the graph state approval_status before resume
                config: RunnableConfig = {"configurable": {"thread_id": run_id}}
                await graph.aupdate_state(
                    config,
                    {"approval_status": "approved", "approver_user_id": current_user.id},
                    as_node="human_approval_node",
                )
                await resume_graph(run_id=run_id, redis=redis, db=bg_db, checkpointer=checkpointer)
                await bg_db.commit()

    background_tasks.add_task(_resume)
    return {"status": "approved", "run_id": run_id}


@router.post("/{run_id}/reject")
async def reject_story(
    run_id: str,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = StoryService(db)
    story = await service.get_by_run_id(run_id)
    if not story:
        raise NotFoundError("Story")

    await service.reject_story(story.id, user_id=current_user.id, reason=body.reason)
    await db.commit()

    # Update graph state so it can end cleanly on next resume
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from app.core.config import settings
    from app.agents.graph import get_graph
    from langchain_core.runnables import RunnableConfig

    return {"status": "rejected", "run_id": run_id}


@router.post("/{run_id}/publish")
async def publish_story(
    run_id: str,
    body: PublishRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    current_user: User = Depends(get_current_user),
):
    service = StoryService(db)
    story = await service.get_by_run_id(run_id)
    if not story:
        raise NotFoundError("Story")

    # SAFETY GATE: never publish without approval
    if story.approval_status != "approved":
        raise ForbiddenError("Story must be approved before publishing")

    from app.models.publication import Publication
    from ulid import ULID

    publication_ids = []
    for target in body.targets:
        pub = Publication(
            id=str(ULID()),
            story_id=story.id,
            platform=target.platform,
            page_id=target.page_id,
            status="scheduled" if target.scheduled_at else "pending",
            scheduled_for=target.scheduled_at,
        )
        db.add(pub)
        await db.flush()
        publication_ids.append(pub.id)

    await db.commit()

    # Dispatch Celery tasks
    from app.workers.tasks.publish_tasks import publish_story_task
    for pub_id in publication_ids:
        pub = await db.get(Publication, pub_id)
        if pub and pub.scheduled_for:
            task = publish_story_task.apply_async(args=[pub_id], eta=pub.scheduled_for)
        else:
            task = publish_story_task.delay(pub_id)
        pub.celery_task_id = task.id
    await db.commit()

    return {"status": "queued", "publication_ids": publication_ids}
