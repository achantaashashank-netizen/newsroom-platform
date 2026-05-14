from langgraph.graph import END, StateGraph

from app.agents.state import NewsroomState


def route_after_verification(state: NewsroomState) -> str:
    tier = state.get("confidence_tier", "low")
    if tier == "low":
        return "reject_node"
    return "summarization_node"


def route_after_approval(state: NewsroomState) -> str:
    status = state.get("approval_status", "pending")
    if status == "approved":
        return "publishing_node"
    if status == "rejected":
        return "end"
    return "human_approval_node"


def route_after_publishing(state: NewsroomState) -> str:
    targets = state.get("publish_targets", [])
    failed = [t for t in targets if t.get("status") == "failed"]
    return "end" if not failed else "end"  # retries handled by Celery


def build_graph(checkpointer=None):
    from app.agents.discovery_agent import discovery_node
    from app.agents.verification_agent import verification_node
    from app.agents.summarization_agent import summarization_node
    from app.agents.media_agent import media_node
    from app.agents.human_approval_node import human_approval_node
    from app.agents.publishing_agent import publishing_node
    from app.agents.reject_node import reject_node

    builder = StateGraph(NewsroomState)

    builder.add_node("discovery_node", discovery_node)
    builder.add_node("verification_node", verification_node)
    builder.add_node("summarization_node", summarization_node)
    builder.add_node("media_node", media_node)
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node("publishing_node", publishing_node)
    builder.add_node("reject_node", reject_node)

    builder.set_entry_point("discovery_node")

    builder.add_edge("discovery_node", "verification_node")
    builder.add_conditional_edges(
        "verification_node",
        route_after_verification,
        {"reject_node": "reject_node", "summarization_node": "summarization_node"},
    )
    builder.add_edge("summarization_node", "media_node")
    builder.add_edge("media_node", "human_approval_node")
    builder.add_conditional_edges(
        "human_approval_node",
        route_after_approval,
        {
            "publishing_node": "publishing_node",
            "end": END,
            "human_approval_node": "human_approval_node",
        },
    )
    builder.add_edge("publishing_node", END)
    builder.add_edge("reject_node", END)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval_node"],
    )


def get_graph(checkpointer=None):
    # Always build fresh when a checkpointer is provided — each run has its own connection
    return build_graph(checkpointer=checkpointer)
