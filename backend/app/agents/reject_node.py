from app.agents.state import NewsroomState
from app.core.logging import get_logger

logger = get_logger(__name__)


async def reject_node(state: NewsroomState) -> dict:
    logger.warning(
        "story_rejected",
        run_id=state["run_id"],
        confidence=state.get("overall_confidence"),
        tier=state.get("confidence_tier"),
        flags=state.get("fake_news_flags", []),
    )
    return {
        "current_node": "reject_node",
        "agent_logs": [{
            "node": "reject_node",
            "type": "done",
            "message": (
                f"Story rejected — confidence too low ({state.get('overall_confidence', 0):.0%}). "
                f"Flags: {', '.join(state.get('fake_news_flags', [])) or 'none'}"
            ),
        }],
    }
