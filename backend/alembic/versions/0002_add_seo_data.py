"""add seo_data to stories

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("seo_data", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("stories", "seo_data")
