from datetime import datetime, timezone

from app.agents.state import NewsroomState
from app.core.logging import get_logger

logger = get_logger(__name__)


async def human_approval_node(state: NewsroomState) -> dict:
    """
    HITL node. The graph is compiled with interrupt_before=["human_approval_node"],
    so execution is paused by LangGraph BEFORE this node runs. When an editor
    approves/rejects via the API, the state is updated and graph.invoke(None, config)
    resumes here — at which point approval_status is already set.
    """
    run_id = state["run_id"]
    approval_status = state.get("approval_status", "pending")

    logger.info("approval_node_resumed", run_id=run_id, approval_status=approval_status)

    return {
        "current_node": "human_approval_node",
        "agent_logs": [{
            "node": "human_approval_node",
            "type": "done",
            "message": f"Editorial decision: {approval_status.upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
    }
