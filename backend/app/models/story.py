from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Story(Base, TimestampMixin):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)

    # Status tracks pipeline progress
    status: Mapped[str] = mapped_column(String, nullable=False, default="discovering", index=True)
    # discovering | verifying | summarizing | media | pending_approval
    # | approved | rejected | publishing | published | failed

    # Verification
    confidence_tier: Mapped[str | None] = mapped_column(String, nullable=True)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    fake_news_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    # Content
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    sub_headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    bullet_points: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    hashtags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    caption_facebook: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_instagram: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Media
    selected_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_card_paths: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    candidate_images: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    # Language
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    translations: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # SEO
    seo_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Approval
    approval_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    human_edits: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Meta
    triggered_by: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by_user_id], back_populates="stories_created")
    approver = relationship("User", foreign_keys=[approved_by_user_id], back_populates="stories_approved")
    agent_runs = relationship("AgentRun", back_populates="story", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="story", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="story", cascade="all, delete-orphan")
    publications = relationship("Publication", back_populates="story", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_stories_created_at_desc", "created_at"),
        Index("idx_stories_confidence", "overall_confidence"),
    )
