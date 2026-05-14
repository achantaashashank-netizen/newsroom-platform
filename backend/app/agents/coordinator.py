import asyncio
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import NewsroomState
from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import emit_sse_event

logger = get_logger(__name__)

# SSE event type constants
EVT_AGENT_START = "agent_start"
EVT_AGENT_PROGRESS = "agent_progress"
EVT_AGENT_DONE = "agent_done"
EVT_AGENT_ERROR = "agent_error"
EVT_STORY_UPDATE = "story_update"
EVT_APPROVAL_REQUIRED = "approval_required"
EVT_PUBLISHED = "published"


async def run_graph(
    run_id: str,
    query: str,
    triggered_by: str,
    redis: aioredis.Redis,
    db: AsyncSession,
    checkpointer,
    user_id: str | None = None,
    story_id: str | None = None,
) -> None:
    from app.agents.graph import get_graph
    from app.models.story import Story
    from app.services.story_service import StoryService

    graph = get_graph(checkpointer=checkpointer)
    story_service = StoryService(db)

    initial_state: NewsroomState = {
        "run_id": run_id,
        "story_id": story_id,
        "triggered_by": triggered_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "raw_sources": [],
        "trending_score": 0.0,
        "discovery_metadata": {},
        "verification_results": [],
        "overall_confidence": 0.0,
        "confidence_tier": "low",
        "fake_news_flags": [],
        "source_reliability_scores": {},
        "headline": "",
        "sub_headline": "",
        "summary": "",
        "bullet_points": [],
        "hashtags": [],
        "caption_facebook": "",
        "caption_instagram": "",
        "language": "en",
        "translations": {},
        "seo_data": {},
        "candidate_images": [],
        "selected_image": None,
        "social_cards": [],
        "media_search_queries": [],
        "approval_status": "pending",
        "human_edits": [],
        "approver_user_id": None,
        "approval_notes": "",
        "approved_at": None,
        "rejection_reason": None,
        "publish_targets": [],
        "celery_task_ids": [],
        "published_at": None,
        "agent_logs": [],
        "current_node": "start",
        "error": None,
        "retry_count": 0,
    }

    config: RunnableConfig = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": settings.LANGGRAPH_RECURSION_LIMIT,
    }

    # Use existing story if id was passed in (router pre-created it), else create one
    if story_id:
        story = await story_service.get_by_id(story_id)
    else:
        story = await story_service.create_story(
            run_id=run_id,
            query=query,
            triggered_by=triggered_by,
            created_by_user_id=user_id,
        )

    logger.info("graph_run_started", run_id=run_id, query=query)

    try:
        async for chunk in graph.astream(initial_state, config=config, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                # LangGraph emits __interrupt__ as a tuple when graph pauses — skip it
                if node_name.startswith("__") or not isinstance(node_output, dict):
                    continue
                await _process_node_output(
                    node_name=node_name,
                    node_output=node_output,
                    run_id=run_id,
                    story_id=story.id,
                    redis=redis,
                    story_service=story_service,
                )

        # Check if graph paused at interrupt (approval required)
        graph_state = await graph.aget_state(config)
        if graph_state.next and "human_approval_node" in graph_state.next:
            current_values = graph_state.values
            await emit_sse_event(redis, run_id, EVT_APPROVAL_REQUIRED, {
                "story_id": story.id,
                "run_id": run_id,
                "confidence_tier": current_values.get("confidence_tier"),
                "headline": current_values.get("headline", ""),
                "summary_preview": (current_values.get("summary") or "")[:200],
                "selected_image_url": (current_values.get("selected_image") or {}).get("url", ""),
            })
            await story_service.update_status(story.id, "pending_approval")
            logger.info("graph_paused_for_approval", run_id=run_id, story_id=story.id)

    except Exception as exc:
        logger.exception("graph_run_error", run_id=run_id, error=str(exc))
        await emit_sse_event(redis, run_id, EVT_AGENT_ERROR, {
            "node": "coordinator",
            "error": str(exc),
            "message": f"Pipeline error: {exc}",
        })
        await story_service.update_status(story.id, "failed")


async def resume_graph(
    run_id: str,
    redis: aioredis.Redis,
    db: AsyncSession,
    checkpointer,
) -> None:
    from app.agents.graph import get_graph
    from app.services.story_service import StoryService

    graph = get_graph(checkpointer=checkpointer)
    story_service = StoryService(db)

    config: RunnableConfig = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": settings.LANGGRAPH_RECURSION_LIMIT,
    }

    story = await story_service.get_by_run_id(run_id)

    try:
        async for chunk in graph.astream(None, config=config, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                if node_name.startswith("__") or not isinstance(node_output, dict):
                    continue
                await _process_node_output(
                    node_name=node_name,
                    node_output=node_output,
                    run_id=run_id,
                    story_id=story.id,
                    redis=redis,
                    story_service=story_service,
                )
    except Exception as exc:
        logger.exception("graph_resume_error", run_id=run_id, error=str(exc))
        await emit_sse_event(redis, run_id, EVT_AGENT_ERROR, {
            "node": "coordinator",
            "error": str(exc),
            "message": f"Resume error: {exc}",
        })


async def _process_node_output(
    node_name: str,
    node_output: dict,
    run_id: str,
    story_id: str,
    redis: aioredis.Redis,
    story_service: Any,
) -> None:
    logs = node_output.get("agent_logs", [])
    for log_entry in logs:
        event_type = {
            "start": EVT_AGENT_START,
            "progress": EVT_AGENT_PROGRESS,
            "done": EVT_AGENT_DONE,
            "error": EVT_AGENT_ERROR,
        }.get(log_entry.get("type", "progress"), EVT_AGENT_PROGRESS)

        await emit_sse_event(redis, run_id, event_type, {
            "node": node_name,
            **log_entry,
        })

    # Sync key story fields to DB after each node completes
    story_update_fields = {
        k: v for k, v in node_output.items()
        if k in {
            "headline", "sub_headline", "summary", "bullet_points",
            "hashtags", "caption_facebook", "caption_instagram",
            "overall_confidence", "confidence_tier", "fake_news_flags",
            "selected_image_url", "candidate_images", "social_card_paths",
            "approval_status", "language", "seo_data",
        }
        and v is not None
    }
    # Handle selected_image → selected_image_url for DB
    if "selected_image" in node_output and node_output["selected_image"]:
        story_update_fields["selected_image_url"] = node_output["selected_image"].get("url")

    if story_update_fields:
        await story_service.update_fields(story_id, story_update_fields)
        await emit_sse_event(redis, run_id, EVT_STORY_UPDATE, story_update_fields)
