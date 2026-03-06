"""新增 M6 合同关闭字段

Revision ID: 0009_add_m6_contract_close
Revises: 0008_add_m5_inventory_exec
Create Date: 2026-03-07 00:50:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009_add_m6_contract_close"
down_revision: str | Sequence[str] | None = "0008_add_m5_inventory_exec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contracts", sa.Column("closed_by", sa.String(length=64), nullable=True))
    op.add_column("contracts", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("contracts", sa.Column("manual_close_by", sa.String(length=64), nullable=True))
    op.add_column("contracts", sa.Column("manual_close_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("contracts", sa.Column("manual_close_diff_amount", sa.Numeric(18, 2), nullable=True))
    op.add_column("contracts", sa.Column("manual_close_diff_qty_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("contracts", "manual_close_diff_qty_json")
    op.drop_column("contracts", "manual_close_diff_amount")
    op.drop_column("contracts", "manual_close_at")
    op.drop_column("contracts", "manual_close_by")
    op.drop_column("contracts", "closed_at")
    op.drop_column("contracts", "closed_by")
