from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RunStoryRequest(BaseModel):
    query: str
    triggered_by: str = "manual"


class RunStoryResponse(BaseModel):
    run_id: str
    story_id: str
    status: str = "discovering"


class ApproveRequest(BaseModel):
    notes: str = ""


class RejectRequest(BaseModel):
    reason: str


class EditRequest(BaseModel):
    field: str
    value: str


class PublishTarget(BaseModel):
    platform: str  # "facebook" | "instagram"
    page_id: str
    scheduled_at: Optional[datetime] = None


class PublishRequest(BaseModel):
    targets: list[PublishTarget]


class StoryRead(BaseModel):
    id: str
    run_id: str
    query: str
    status: str
    confidence_tier: Optional[str] = None
    overall_confidence: Optional[float] = None
    fake_news_flags: Optional[list] = None
    headline: Optional[str] = None
    sub_headline: Optional[str] = None
    summary: Optional[str] = None
    bullet_points: Optional[list] = None
    hashtags: Optional[list] = None
    caption_facebook: Optional[str] = None
    caption_instagram: Optional[str] = None
    selected_image_url: Optional[str] = None
    candidate_images: Optional[list] = None
    social_card_paths: Optional[dict] = None
    seo_data: Optional[dict] = None
    language: str = "en"
    approval_status: str = "pending"
    human_edits: Optional[list] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    triggered_by: str = "manual"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
