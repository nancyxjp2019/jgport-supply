"""新增 M8 供应商发货确认字段

Revision ID: 0012_add_m8_supplier_delivery_confirm
Revises: 0011_add_m8_wechat_auth
Create Date: 2026-03-07 10:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012_m8_supplier_confirm"
down_revision: str | Sequence[str] | None = "0011_add_m8_wechat_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "purchase_orders",
        sa.Column("supplier_confirm_comment", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("supplier_confirmed_by", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("supplier_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE purchase_orders SET status = '待供应商确认' WHERE status = '已创建'"
    )
    op.alter_column(
        "purchase_orders",
        "status",
        existing_type=sa.String(length=24),
        server_default=sa.text("'待供应商确认'"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "purchase_orders",
        "status",
        existing_type=sa.String(length=24),
        server_default=sa.text("'已创建'"),
        existing_nullable=False,
    )
    op.execute(
        "UPDATE purchase_orders SET status = '已创建' WHERE status = '待供应商确认'"
    )
    op.drop_column("purchase_orders", "supplier_confirmed_at")
    op.drop_column("purchase_orders", "supplier_confirmed_by")
    op.drop_column("purchase_orders", "supplier_confirm_comment")
