"""add transport info and system configs

Revision ID: 7d5f54c17f2a
Revises: 1fb473659c97
Create Date: 2026-02-11 15:35:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "7d5f54c17f2a"
down_revision: str | None = "1fb473659c97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("transport_info_json", sa.JSON(), nullable=True))
    op.add_column("orders", sa.Column("transport_attachment_urls_json", sa.JSON(), nullable=True))

    op.create_table(
        "system_configs",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("system_configs")
    op.drop_column("orders", "transport_attachment_urls_json")
    op.drop_column("orders", "transport_info_json")
