"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="editor"),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    op.create_table(
        "stories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="discovering"),
        sa.Column("confidence_tier", sa.String(), nullable=True),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("fake_news_flags", postgresql.JSONB(), nullable=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("sub_headline", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("bullet_points", postgresql.JSONB(), nullable=True),
        sa.Column("hashtags", postgresql.JSONB(), nullable=True),
        sa.Column("caption_facebook", sa.Text(), nullable=True),
        sa.Column("caption_instagram", sa.Text(), nullable=True),
        sa.Column("selected_image_url", sa.Text(), nullable=True),
        sa.Column("social_card_paths", postgresql.JSONB(), nullable=True),
        sa.Column("candidate_images", postgresql.JSONB(), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("translations", postgresql.JSONB(), nullable=True),
        sa.Column("approval_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("human_edits", postgresql.JSONB(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(), nullable=False, server_default="manual"),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("approved_by_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_stories_run_id", "stories", ["run_id"], unique=True)
    op.create_index("idx_stories_status", "stories", ["status"])
    op.create_index("idx_stories_created_at_desc", "stories", ["created_at"])
    op.create_index("idx_stories_confidence", "stories", ["overall_confidence"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("story_id", sa.String(), nullable=False),
        sa.Column("node_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("output_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("token_usage", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_agent_runs_story_id", "agent_runs", ["story_id"])

    op.create_table(
        "verifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("story_id", sa.String(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("corroborated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confidence_contribution", sa.Float(), nullable=True),
        sa.Column("claim_matches", postgresql.JSONB(), nullable=True),
        sa.Column("contradictions", postgresql.JSONB(), nullable=True),
        sa.Column("gdelt_event_ids", postgresql.JSONB(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_verifications_story_id", "verifications", ["story_id"])

    op.create_table(
        "social_accounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("page_id", sa.String(), nullable=False),
        sa.Column("page_name", sa.String(), nullable=False),
        sa.Column("page_picture_url", sa.String(), nullable=True),
        sa.Column("instagram_account_id", sa.String(), nullable=True),
        sa.Column("access_token", sa.String(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "page_id", name="uq_social_accounts_platform_page"),
    )
    op.create_index("idx_social_accounts_user_id", "social_accounts", ["user_id"])

    op.create_table(
        "drafts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("story_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("hashtags", postgresql.JSONB(), nullable=True),
        sa.Column("human_edits", postgresql.JSONB(), nullable=True),
        sa.Column("saved_by_user_id", sa.String(), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saved_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_drafts_story_id", "drafts", ["story_id"])

    op.create_table(
        "publications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("story_id", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("page_id", sa.String(), nullable=False),
        sa.Column("platform_post_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("celery_task_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_publications_story_id", "publications", ["story_id"])
    op.create_index("idx_publications_status", "publications", ["status"])


def downgrade() -> None:
    op.drop_table("publications")
    op.drop_table("drafts")
    op.drop_table("social_accounts")
    op.drop_table("verifications")
    op.drop_table("agent_runs")
    op.drop_table("stories")
    op.drop_table("users")
