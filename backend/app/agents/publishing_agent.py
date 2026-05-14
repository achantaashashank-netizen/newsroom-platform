from datetime import datetime, timezone

from app.agents.state import NewsroomState
from app.core.logging import get_logger

logger = get_logger(__name__)


async def publishing_agent_node(state: NewsroomState) -> dict:
    """
    Dispatches Celery publish tasks for each approved publish target.
    Actual Meta API calls happen inside the Celery worker.
    """
    run_id = state["run_id"]
    publish_targets = state.get("publish_targets", [])

    logs = [{
        "node": "publishing_node",
        "type": "start",
        "message": f"Dispatching publish tasks for {len(publish_targets)} platform(s)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]

    if not publish_targets:
        logs.append({
            "node": "publishing_node",
            "type": "done",
            "message": "No publish targets configured — skipping publishing",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"current_node": "publishing_node", "agent_logs": logs}

    updated_targets = []
    celery_task_ids = []

    for target in publish_targets:
        try:
            from app.workers.tasks.publish_tasks import publish_story_task

            platform = target["platform"]
            page_id = target["page_id"]
            scheduled_at = target.get("scheduled_at")

            # Celery task dispatch — actual publishing happens in worker
            # Publication record must be created in DB before this point
            # (done by the publishing router before graph resume)
            task = publish_story_task.delay(
                publication_id=target.get("publication_id", ""),
            )
            celery_task_ids.append(task.id)

            updated_target = {**target, "status": "scheduled" if scheduled_at else "pending"}
            updated_targets.append(updated_target)

            logs.append({
                "node": "publishing_node",
                "type": "progress",
                "message": f"Queued for {platform} (page: {page_id}) — task {task.id[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        except Exception as exc:
            logger.warning("publish_dispatch_error", target=target, error=str(exc))
            updated_targets.append({**target, "status": "failed"})
            logs.append({
                "node": "publishing_node",
                "type": "error",
                "message": f"Failed to queue {target['platform']}: {exc}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    logs.append({
        "node": "publishing_node",
        "type": "done",
        "message": f"Publishing queued — {len(celery_task_ids)} task(s) dispatched to Celery",
        "progress": 100,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "publish_targets": updated_targets,
        "celery_task_ids": celery_task_ids,
        "current_node": "publishing_node",
        "agent_logs": logs,
    }


# Alias used in graph.py
publishing_node = publishing_agent_node
