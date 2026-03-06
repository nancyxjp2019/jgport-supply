"""新增 M3 订单域表结构

Revision ID: 0005_add_m3_order_domain
Revises: 0004_add_m2_contract_domain
Create Date: 2026-03-06 13:15:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_add_m3_order_domain"
down_revision: str | Sequence[str] | None = "0004_add_m2_contract_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("sales_contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("oil_product_id", sa.String(length=64), nullable=False),
        sa.Column("qty_ordered", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'草稿'")),
        sa.Column("submit_comment", sa.String(length=256), nullable=True),
        sa.Column("ops_comment", sa.String(length=256), nullable=True),
        sa.Column("finance_comment", sa.String(length=256), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("ops_approved_by", sa.String(length=64), nullable=True),
        sa.Column("finance_approved_by", sa.String(length=64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ops_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finance_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("order_no", name="uq_sales_order_no"),
    )
    op.create_index("ix_sales_orders_order_no", "sales_orders", ["order_no"])
    op.create_index("ix_sales_orders_sales_contract_id", "sales_orders", ["sales_contract_id"])
    op.create_index("ix_sales_orders_oil_product_id", "sales_orders", ["oil_product_id"])
    op.create_index("ix_sales_orders_status", "sales_orders", ["status"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("purchase_contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("oil_product_id", sa.String(length=64), nullable=False),
        sa.Column("qty_ordered", sa.Numeric(18, 3), nullable=False),
        sa.Column("payable_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'已创建'")),
        sa.Column("zero_pay_exception_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("order_no", name="uq_purchase_order_no"),
        sa.UniqueConstraint("source_sales_order_id", name="uq_purchase_order_source_sales_order"),
    )
    op.create_index("ix_purchase_orders_order_no", "purchase_orders", ["order_no"])
    op.create_index("ix_purchase_orders_purchase_contract_id", "purchase_orders", ["purchase_contract_id"])
    op.create_index("ix_purchase_orders_source_sales_order_id", "purchase_orders", ["source_sales_order_id"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_oil_product_id", "purchase_orders", ["oil_product_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])

    op.create_table(
        "sales_order_derivative_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_doc_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'待处理'")),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("idempotency_key", name="uq_sales_order_derivative_task_key"),
    )
    op.create_index("ix_sales_order_derivative_tasks_sales_order_id", "sales_order_derivative_tasks", ["sales_order_id"])
    op.create_index("ix_sales_order_derivative_tasks_target_doc_type", "sales_order_derivative_tasks", ["target_doc_type"])
    op.create_index("ix_sales_order_derivative_tasks_status", "sales_order_derivative_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_sales_order_derivative_tasks_status", table_name="sales_order_derivative_tasks")
    op.drop_index("ix_sales_order_derivative_tasks_target_doc_type", table_name="sales_order_derivative_tasks")
    op.drop_index("ix_sales_order_derivative_tasks_sales_order_id", table_name="sales_order_derivative_tasks")
    op.drop_table("sales_order_derivative_tasks")

    op.drop_index("ix_purchase_orders_status", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_oil_product_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_supplier_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_source_sales_order_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_purchase_contract_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_order_no", table_name="purchase_orders")
    op.drop_table("purchase_orders")

    op.drop_index("ix_sales_orders_status", table_name="sales_orders")
    op.drop_index("ix_sales_orders_oil_product_id", table_name="sales_orders")
    op.drop_index("ix_sales_orders_sales_contract_id", table_name="sales_orders")
    op.drop_index("ix_sales_orders_order_no", table_name="sales_orders")
    op.drop_table("sales_orders")
