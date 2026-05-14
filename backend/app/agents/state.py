import operator
from typing import Annotated, Literal, Optional, TypedDict


class SourceItem(TypedDict):
    url: str
    title: str
    source_name: str
    published_at: str
    raw_text: str
    feed_origin: str  # "rss" | "newsapi" | "gdelt" | "hackernews" | "playwright"


class VerificationResult(TypedDict):
    source_url: str
    source_name: str
    corroborated: bool
    confidence_contribution: float
    reliability_score: float
    claim_matches: list[str]
    contradictions: list[str]


class MediaAsset(TypedDict):
    url: str
    local_path: Optional[str]
    relevance_score: float
    alt_text: str
    source_attribution: str
    is_ai_generated: bool
    width: int
    height: int


class SocialCard(TypedDict):
    platform: str  # "facebook" | "instagram"
    image_path: str
    dimensions: list[int]  # [width, height]


class HumanEdit(TypedDict):
    field: str
    original: str
    edited: str
    editor_user_id: str
    edited_at: str


class PublishTarget(TypedDict):
    platform: str  # "facebook" | "instagram"
    page_id: str
    scheduled_at: Optional[str]  # ISO8601 or None = immediate
    status: str  # "pending" | "published" | "failed" | "scheduled"
    platform_post_id: Optional[str]


class NewsroomState(TypedDict):
    # ── Identity ──────────────────────────────────────────────────────────────
    run_id: str
    story_id: Optional[str]
    triggered_by: str  # "scheduler" | "manual"
    created_at: str

    # ── Discovery ─────────────────────────────────────────────────────────────
    query: str
    raw_sources: list[SourceItem]
    trending_score: float
    discovery_metadata: dict

    # ── Verification ──────────────────────────────────────────────────────────
    verification_results: list[VerificationResult]
    overall_confidence: float
    confidence_tier: Literal["low", "medium", "high"]
    fake_news_flags: list[str]
    source_reliability_scores: dict  # url -> reliability_score

    # ── Summarization ─────────────────────────────────────────────────────────
    headline: str
    sub_headline: str
    summary: str
    bullet_points: list[str]
    hashtags: list[str]
    caption_facebook: str
    caption_instagram: str
    language: str
    translations: dict  # lang_code -> {headline, summary, caption_*}
    seo_data: dict      # {score, focus_keyword, secondary_keywords, meta_description, slug, readability, tips}

    # ── Media ─────────────────────────────────────────────────────────────────
    candidate_images: list[MediaAsset]
    selected_image: Optional[MediaAsset]
    social_cards: list[SocialCard]
    media_search_queries: list[str]

    # ── Human Approval (LangGraph interrupt point) ────────────────────────────
    approval_status: Literal["pending", "approved", "rejected", "editing"]
    human_edits: Annotated[list[HumanEdit], operator.add]
    approver_user_id: Optional[str]
    approval_notes: str
    approved_at: Optional[str]
    rejection_reason: Optional[str]

    # ── Publishing ────────────────────────────────────────────────────────────
    publish_targets: list[PublishTarget]
    celery_task_ids: list[str]
    published_at: Optional[str]

    # ── Agent Execution Log (append-only, streamed via SSE) ───────────────────
    agent_logs: Annotated[list[dict], operator.add]
    current_node: str
    error: Optional[str]
    retry_count: int
