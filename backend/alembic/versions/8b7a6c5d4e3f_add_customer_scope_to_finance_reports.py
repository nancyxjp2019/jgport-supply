"""add customer scope to finance reports

Revision ID: 8b7a6c5d4e3f
Revises: c3f8a1b2d4e5
Create Date: 2026-02-28 23:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "8b7a6c5d4e3f"
down_revision: str | None = "c3f8a1b2d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("finance_reports", schema=None) as batch_op:
        batch_op.add_column(sa.Column("scope_customer_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_finance_reports_scope_customer_id"), ["scope_customer_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("finance_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_finance_reports_scope_customer_id"))
        batch_op.drop_column("scope_customer_id")
