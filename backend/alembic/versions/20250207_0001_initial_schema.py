"""initial schema

Revision ID: 20250207_0001
Revises:
Create Date: 2025-02-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20250207_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "email_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.String(length=255), unique=True, nullable=True),
        sa.Column("from_address", sa.String(length=255), nullable=False, index=True),
        sa.Column("to_address", sa.String(length=255), nullable=False, index=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body_preview", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("in_registry", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trust_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analyzed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("technical_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("linguistic_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("behavioral_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("contextual_score", sa.Float(), nullable=False, server_default="0"),
    )

    op.create_table(
        "trusted_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email_address", sa.String(length=255), nullable=False, unique=True),
        sa.Column("domain", sa.String(length=255), nullable=False, index=True),
        sa.Column("organization_name", sa.String(length=255), nullable=True),
        sa.Column("trust_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("added_by", sa.Integer(), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("total_emails", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_email_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "phishing_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporter_id", sa.Integer(), nullable=True, index=True),
        sa.Column("message_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("from_address", sa.String(length=255), nullable=False, index=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("investigated_by", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("reported_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "threat_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("affected_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_address", sa.String(length=255), nullable=True),
        sa.Column("indicators", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("threat_alerts")
    op.drop_table("phishing_reports")
    op.drop_table("trusted_registry")
    op.drop_table("email_analyses")
    op.drop_table("users")
