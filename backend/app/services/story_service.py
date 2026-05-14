from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.story import Story

logger = get_logger(__name__)


def _new_id() -> str:
    from ulid import ULID
    return str(ULID())


class StoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_story(
        self,
        run_id: str,
        query: str,
        triggered_by: str,
        created_by_user_id: str | None = None,
    ) -> Story:
        story = Story(
            id=_new_id(),
            run_id=run_id,
            query=query,
            triggered_by=triggered_by,
            status="discovering",
            created_by_user_id=created_by_user_id,
        )
        self.db.add(story)
        await self.db.flush()
        return story

    async def get_by_id(self, story_id: str) -> Story | None:
        result = await self.db.execute(select(Story).where(Story.id == story_id))
        return result.scalar_one_or_none()

    async def get_by_run_id(self, run_id: str) -> Story | None:
        result = await self.db.execute(select(Story).where(Story.run_id == run_id))
        return result.scalar_one_or_none()

    async def update_status(self, story_id: str, status: str) -> None:
        story = await self.get_by_id(story_id)
        if story:
            story.status = status
            await self.db.flush()

    async def update_fields(self, story_id: str, fields: dict) -> None:
        story = await self.get_by_id(story_id)
        if not story:
            return
        for key, value in fields.items():
            if hasattr(story, key):
                setattr(story, key, value)
        await self.db.flush()

    async def approve_story(self, story_id: str, user_id: str, notes: str = "") -> Story | None:
        story = await self.get_by_id(story_id)
        if not story:
            return None
        story.approval_status = "approved"
        story.approved_by_user_id = user_id
        story.approved_at = datetime.now(timezone.utc)
        story.status = "approved"
        await self.db.flush()
        return story

    async def reject_story(self, story_id: str, user_id: str, reason: str) -> Story | None:
        story = await self.get_by_id(story_id)
        if not story:
            return None
        story.approval_status = "rejected"
        story.rejection_reason = reason
        story.status = "rejected"
        await self.db.flush()
        return story

    async def list_stories(self, limit: int = 20, offset: int = 0) -> list[Story]:
        result = await self.db.execute(
            select(Story).order_by(Story.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
