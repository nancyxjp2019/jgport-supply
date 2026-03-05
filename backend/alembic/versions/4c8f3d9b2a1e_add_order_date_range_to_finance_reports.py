"""add order date range to finance reports

Revision ID: 4c8f3d9b2a1e
Revises: 2f3c9a1d4b7e
Create Date: 2026-02-20 13:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "4c8f3d9b2a1e"
down_revision: str | None = "2f3c9a1d4b7e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("finance_reports", sa.Column("order_date_from", sa.Date(), nullable=True))
    op.add_column("finance_reports", sa.Column("order_date_to", sa.Date(), nullable=True))
    op.create_index(op.f("ix_finance_reports_order_date_from"), "finance_reports", ["order_date_from"], unique=False)
    op.create_index(op.f("ix_finance_reports_order_date_to"), "finance_reports", ["order_date_to"], unique=False)
    op.execute(
        """
        UPDATE finance_reports
        SET order_date_from = DATE(created_at),
            order_date_to = DATE(created_at)
        WHERE order_date_from IS NULL OR order_date_to IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_finance_reports_order_date_to"), table_name="finance_reports")
    op.drop_index(op.f("ix_finance_reports_order_date_from"), table_name="finance_reports")
    op.drop_column("finance_reports", "order_date_to")
    op.drop_column("finance_reports", "order_date_from")
