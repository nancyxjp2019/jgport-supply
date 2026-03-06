"""新增 M4 资金单据与关系表

Revision ID: 0006_add_m4_funds_domain
Revises: 0005_add_m3_order_domain
Create Date: 2026-03-06 17:30:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_add_m4_funds_domain"
down_revision: str | Sequence[str] | None = "0005_add_m3_order_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "receipt_docs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("doc_no", sa.String(length=64), nullable=False),
        sa.Column("doc_type", sa.String(length=16), nullable=False),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount_actual", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'草稿'")),
        sa.Column("voucher_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("voucher_exempt_reason", sa.String(length=256), nullable=True),
        sa.Column("refund_status", sa.String(length=16), nullable=False, server_default=sa.text("'未退款'")),
        sa.Column("refund_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("confirmed_by", sa.String(length=64), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("doc_no", name="uq_receipt_doc_no"),
    )
    op.create_index("ix_receipt_docs_doc_no", "receipt_docs", ["doc_no"])
    op.create_index("ix_receipt_docs_doc_type", "receipt_docs", ["doc_type"])
    op.create_index("ix_receipt_docs_contract_id", "receipt_docs", ["contract_id"])
    op.create_index("ix_receipt_docs_sales_order_id", "receipt_docs", ["sales_order_id"])
    op.create_index("ix_receipt_docs_status", "receipt_docs", ["status"])

    op.create_table(
        "payment_docs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("doc_no", sa.String(length=64), nullable=False),
        sa.Column("doc_type", sa.String(length=16), nullable=False),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount_actual", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'草稿'")),
        sa.Column("voucher_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("voucher_exempt_reason", sa.String(length=256), nullable=True),
        sa.Column("refund_status", sa.String(length=16), nullable=False, server_default=sa.text("'未退款'")),
        sa.Column("refund_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("confirmed_by", sa.String(length=64), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("doc_no", name="uq_payment_doc_no"),
    )
    op.create_index("ix_payment_docs_doc_no", "payment_docs", ["doc_no"])
    op.create_index("ix_payment_docs_doc_type", "payment_docs", ["doc_type"])
    op.create_index("ix_payment_docs_contract_id", "payment_docs", ["contract_id"])
    op.create_index("ix_payment_docs_purchase_order_id", "payment_docs", ["purchase_order_id"])
    op.create_index("ix_payment_docs_status", "payment_docs", ["status"])

    op.create_table(
        "doc_relations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_doc_type", sa.String(length=32), nullable=False),
        sa.Column("source_doc_id", sa.Integer(), nullable=False),
        sa.Column("target_doc_type", sa.String(length=32), nullable=False),
        sa.Column("target_doc_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint(
            "source_doc_type",
            "source_doc_id",
            "target_doc_type",
            "target_doc_id",
            "relation_type",
            name="uq_doc_relation_unique",
        ),
    )
    op.create_index("ix_doc_relations_source_doc_type", "doc_relations", ["source_doc_type"])
    op.create_index("ix_doc_relations_source_doc_id", "doc_relations", ["source_doc_id"])
    op.create_index("ix_doc_relations_target_doc_type", "doc_relations", ["target_doc_type"])
    op.create_index("ix_doc_relations_target_doc_id", "doc_relations", ["target_doc_id"])
    op.create_index("ix_doc_relations_relation_type", "doc_relations", ["relation_type"])


def downgrade() -> None:
    op.drop_index("ix_doc_relations_relation_type", table_name="doc_relations")
    op.drop_index("ix_doc_relations_target_doc_id", table_name="doc_relations")
    op.drop_index("ix_doc_relations_target_doc_type", table_name="doc_relations")
    op.drop_index("ix_doc_relations_source_doc_id", table_name="doc_relations")
    op.drop_index("ix_doc_relations_source_doc_type", table_name="doc_relations")
    op.drop_table("doc_relations")

    op.drop_index("ix_payment_docs_status", table_name="payment_docs")
    op.drop_index("ix_payment_docs_purchase_order_id", table_name="payment_docs")
    op.drop_index("ix_payment_docs_contract_id", table_name="payment_docs")
    op.drop_index("ix_payment_docs_doc_type", table_name="payment_docs")
    op.drop_index("ix_payment_docs_doc_no", table_name="payment_docs")
    op.drop_table("payment_docs")

    op.drop_index("ix_receipt_docs_status", table_name="receipt_docs")
    op.drop_index("ix_receipt_docs_sales_order_id", table_name="receipt_docs")
    op.drop_index("ix_receipt_docs_contract_id", table_name="receipt_docs")
    op.drop_index("ix_receipt_docs_doc_type", table_name="receipt_docs")
    op.drop_index("ix_receipt_docs_doc_no", table_name="receipt_docs")
    op.drop_table("receipt_docs")
