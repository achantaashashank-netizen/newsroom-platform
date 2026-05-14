from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String, nullable=True)
    reliability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    corroborated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence_contribution: Mapped[float | None] = mapped_column(Float, nullable=True)
    claim_matches: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    contradictions: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    gdelt_event_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    checked_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    story = relationship("Story", back_populates="verifications")
