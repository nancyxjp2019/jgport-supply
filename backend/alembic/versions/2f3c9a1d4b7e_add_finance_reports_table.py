"""add finance reports table

Revision ID: 2f3c9a1d4b7e
Revises: 9a2c8f6d1b3e
Create Date: 2026-02-14 18:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2f3c9a1d4b7e"
down_revision: str | None = "9a2c8f6d1b3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "finance_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_name", sa.String(length=128), nullable=False),
        sa.Column("as_of_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", sa.Integer(), nullable=False),
        sa.Column("file_key", sa.String(length=512), nullable=False),
        sa.Column("file_url", sa.String(length=512), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_key"),
    )
    op.create_index(op.f("ix_finance_reports_as_of_at"), "finance_reports", ["as_of_at"], unique=False)
    op.create_index(op.f("ix_finance_reports_created_at"), "finance_reports", ["created_at"], unique=False)
    op.create_index(op.f("ix_finance_reports_generated_by"), "finance_reports", ["generated_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_finance_reports_generated_by"), table_name="finance_reports")
    op.drop_index(op.f("ix_finance_reports_created_at"), table_name="finance_reports")
    op.drop_index(op.f("ix_finance_reports_as_of_at"), table_name="finance_reports")
    op.drop_table("finance_reports")
