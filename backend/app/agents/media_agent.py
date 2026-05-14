from datetime import datetime, timezone

from app.agents.state import MediaAsset, NewsroomState
from app.core.logging import get_logger
from app.tools.image_tools import generate_dalle_cartoon, fetch_article_image, generate_social_card

logger = get_logger(__name__)


async def media_node(state: NewsroomState) -> dict:
    run_id = state["run_id"]
    headline = state.get("headline", state["query"])
    summary = state.get("summary", "")
    bullet_points = state.get("bullet_points", [])
    raw_sources = state.get("raw_sources", [])

    logs = [{
        "node": "media_node",
        "type": "start",
        "message": "Generating editorial cartoon illustration...",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]

    try:
        # Try AI cartoon first; fall back to extracting image from source articles
        image_url = await generate_dalle_cartoon(run_id, headline, summary, bullet_points)

        if not image_url and raw_sources:
            logs.append({
                "node": "media_node",
                "type": "progress",
                "message": "AI image unavailable — extracting best image from source articles...",
                "progress": 40,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            source_urls = [s["url"] for s in raw_sources if s.get("url")]
            image_url = await fetch_article_image(source_urls, run_id)

        logs.append({
            "node": "media_node",
            "type": "progress",
            "message": "Image ready — creating social media cards",
            "progress": 65,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        selected_image: MediaAsset | None = None
        social_card_paths: dict[str, str] = {}

        if image_url:
            is_ai = image_url.endswith("_cartoon.jpg") and not raw_sources
            selected_image = {
                "url": image_url,
                "local_path": None,
                "relevance_score": 1.0,
                "alt_text": headline,
                "source_attribution": "gpt-image-1 (AI Generated)" if is_ai else "Article Source Image",
                "is_ai_generated": is_ai,
                "width": 1536,
                "height": 1024,
            }

            for platform in ["facebook", "instagram"]:
                card_path = generate_social_card(headline, "Newsroom", image_url, platform, run_id)
                if card_path:
                    social_card_paths[platform] = card_path

        logs.append({
            "node": "media_node",
            "type": "done",
            "message": (
                f"Media ready — AI cartoon generated, {len(social_card_paths)} social cards created"
                if image_url else
                "Media skipped — set OPENAI_API_KEY to enable AI cartoon generation"
            ),
            "progress": 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("media_complete", run_id=run_id, has_image=bool(image_url), cards=len(social_card_paths))

        return {
            "candidate_images": [selected_image] if selected_image else [],
            "selected_image": selected_image,
            "social_card_paths": social_card_paths,
            "current_node": "media_node",
            "agent_logs": logs,
        }

    except Exception as exc:
        logger.exception("media_error", run_id=run_id, error=str(exc))
        logs.append({
            "node": "media_node",
            "type": "error",
            "message": f"Media agent error: {exc}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "candidate_images": [],
            "selected_image": None,
            "social_card_paths": {},
            "error": str(exc),
            "current_node": "media_node",
            "agent_logs": logs,
        }
