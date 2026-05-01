"""Add body_text and raw headers to email_analyses

Revision ID: 20251211_01
Revises: 
Create Date: 2025-12-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251211_01"
down_revision = "20250207_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("email_analyses", sa.Column("body_text", sa.Text(), nullable=True))
    op.add_column("email_analyses", sa.Column("raw_headers", postgresql.JSONB(), nullable=True))
    op.add_column("email_analyses", sa.Column("raw_email_path", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("email_analyses", "raw_email_path")
    op.drop_column("email_analyses", "raw_headers")
    op.drop_column("email_analyses", "body_text")
