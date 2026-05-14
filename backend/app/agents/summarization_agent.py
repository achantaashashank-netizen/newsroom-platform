from datetime import datetime, timezone
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.state import NewsroomState
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StoryOutput(BaseModel):
    headline: str = Field(description="Compelling news headline, max 15 words")
    sub_headline: str = Field(description="Explanatory sub-headline, max 25 words")
    summary: str = Field(description="2-3 paragraph factual summary of the story")
    bullet_points: list[str] = Field(description="5 key facts as concise bullet points")
    hashtags: list[str] = Field(description="8-12 relevant hashtags without # symbol")
    caption_facebook: str = Field(description="Facebook post caption, 150-300 chars, engaging tone")
    caption_instagram: str = Field(description="Instagram caption, max 2200 chars, includes hashtags naturally")
    language: str = Field(description="ISO 639-1 language code of the primary sources, e.g. 'en'")


class SEOOutput(BaseModel):
    seo_score: int = Field(description="Overall SEO score 0-100 based on keyword usage, headline quality, and content structure")
    focus_keyword: str = Field(description="Primary keyword phrase (2-4 words) that best represents this article")
    secondary_keywords: list[str] = Field(description="4-6 secondary keywords relevant to the story")
    meta_description: str = Field(description="SEO meta description, exactly 120-160 chars, includes focus keyword, action-oriented")
    slug: str = Field(description="URL-friendly slug: lowercase, hyphens only, 40-70 chars, contains focus keyword")
    readability: str = Field(description="Reading level — one of: 'Easy (Grade 6-8)', 'Standard (Grade 9-12)', 'Advanced (Grade 13+)'")
    tips: list[str] = Field(description="2-3 specific actionable tips to improve SEO for this exact article")


def _build_source_context(raw_sources: list, max_sources: int = 8) -> str:
    top_sources = raw_sources[:max_sources]
    lines = []
    for s in top_sources:
        lines.append(f"SOURCE [{s['source_name']}]:\nTitle: {s['title']}\nContent: {s['raw_text'][:500]}")
    return "\n\n---\n\n".join(lines)


async def summarization_node(state: NewsroomState) -> dict:
    run_id = state["run_id"]
    query = state["query"]
    raw_sources = state.get("raw_sources", [])
    confidence_tier = state.get("confidence_tier", "medium")

    logs = [{
        "node": "summarization_node",
        "type": "start",
        "message": "Generating AI-powered story summary, headline, and social captions",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]

    if not raw_sources:
        logs.append({
            "node": "summarization_node",
            "type": "error",
            "message": "No source material to summarize",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"agent_logs": logs, "current_node": "summarization_node"}

    try:
        llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=2048,
        )
        structured_llm = llm.with_structured_output(StoryOutput)

        source_context = _build_source_context(raw_sources)

        system_prompt = """You are a senior editor at a world-class news agency.
Your task is to synthesize multiple news sources into accurate, engaging content.
Be factual, balanced, and avoid sensationalism.
Write with authority and clarity."""

        user_prompt = f"""Synthesize the following news sources about: "{query}"

Confidence tier: {confidence_tier.upper()} — reflect appropriate certainty in your language.

{source_context}

Generate comprehensive editorial content including a headline, sub-headline,
full summary, bullet points, and social media captions for Facebook and Instagram."""

        logs.append({
            "node": "summarization_node",
            "type": "progress",
            "message": "Sending to Claude for editorial synthesis...",
            "progress": 30,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result: StoryOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])

        logs.append({
            "node": "summarization_node",
            "type": "progress",
            "message": "Running SEO analysis...",
            "progress": 75,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # SEO scoring — lightweight haiku call so it doesn't slow the pipeline
        seo_data: dict = {}
        try:
            seo_llm = ChatAnthropic(
                model="claude-haiku-4-5-20251001",
                api_key=settings.ANTHROPIC_API_KEY,
                max_tokens=600,
            )
            seo_result: SEOOutput = await seo_llm.with_structured_output(SEOOutput).ainvoke([
                SystemMessage(content="You are an expert SEO editor for a major news publication. Analyze the article below and return a structured SEO assessment."),
                HumanMessage(content=(
                    f"Headline: {result.headline}\n\n"
                    f"Summary:\n{result.summary}\n\n"
                    f"Key facts:\n" + "\n".join(f"- {b}" for b in result.bullet_points)
                )),
            ])
            seo_data = {
                "score": seo_result.seo_score,
                "focus_keyword": seo_result.focus_keyword,
                "secondary_keywords": seo_result.secondary_keywords,
                "meta_description": seo_result.meta_description,
                "slug": seo_result.slug,
                "readability": seo_result.readability,
                "tips": seo_result.tips,
            }
            logger.info("seo_complete", run_id=run_id, score=seo_result.seo_score)
        except Exception as seo_exc:
            logger.warning("seo_error", run_id=run_id, error=str(seo_exc))

        logs.append({
            "node": "summarization_node",
            "type": "done",
            "message": (
                f"Editorial complete — '{result.headline[:55]}...' "
                f"| SEO score: {seo_data.get('score', '?')}/100"
            ),
            "progress": 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("summarization_complete", run_id=run_id, headline=result.headline[:80])

        return {
            "headline": result.headline,
            "sub_headline": result.sub_headline,
            "summary": result.summary,
            "bullet_points": result.bullet_points,
            "hashtags": result.hashtags,
            "caption_facebook": result.caption_facebook,
            "caption_instagram": result.caption_instagram,
            "language": result.language or "en",
            "seo_data": seo_data,
            "current_node": "summarization_node",
            "agent_logs": logs,
        }

    except Exception as exc:
        logger.exception("summarization_error", run_id=run_id, error=str(exc))
        logs.append({
            "node": "summarization_node",
            "type": "error",
            "message": f"Summarization failed: {exc}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "error": str(exc),
            "current_node": "summarization_node",
            "agent_logs": logs,
        }
