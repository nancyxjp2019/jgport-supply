"""初始化 V6 基础表结构

Revision ID: 0001_init_v6_schema
Revises:
Create Date: 2026-03-05 13:45:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_init_v6_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_action", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=128), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_business_logs_event_type", "business_logs", ["event_type"])
    op.create_index("ix_business_logs_created_at", "business_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_business_logs_created_at", table_name="business_logs")
    op.drop_index("ix_business_logs_event_type", table_name="business_logs")
    op.drop_table("business_logs")
