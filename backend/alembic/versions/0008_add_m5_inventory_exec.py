"""新增 M5 出入库与履约累计表

Revision ID: 0008_add_m5_inventory_exec
Revises: 0007_add_m4_doc_attach
Create Date: 2026-03-06 23:40:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008_add_m5_inventory_exec"
down_revision: str | Sequence[str] | None = "0007_add_m4_doc_attach"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inbound_docs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("doc_no", sa.String(length=64), nullable=False),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("oil_product_id", sa.String(length=64), nullable=False),
        sa.Column("warehouse_id", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("actual_qty", sa.Numeric(18, 3), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'草稿'")),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("submitted_by", sa.String(length=64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("doc_no", name="uq_inbound_doc_no"),
        sa.UniqueConstraint("idempotency_key", name="uq_inbound_doc_idempotency_key"),
    )
    op.create_index("ix_inbound_docs_doc_no", "inbound_docs", ["doc_no"])
    op.create_index("ix_inbound_docs_contract_id", "inbound_docs", ["contract_id"])
    op.create_index("ix_inbound_docs_purchase_order_id", "inbound_docs", ["purchase_order_id"])
    op.create_index("ix_inbound_docs_oil_product_id", "inbound_docs", ["oil_product_id"])
    op.create_index("ix_inbound_docs_warehouse_id", "inbound_docs", ["warehouse_id"])
    op.create_index("ix_inbound_docs_source_type", "inbound_docs", ["source_type"])
    op.create_index("ix_inbound_docs_idempotency_key", "inbound_docs", ["idempotency_key"])
    op.create_index("ix_inbound_docs_status", "inbound_docs", ["status"])

    op.create_table(
        "outbound_docs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("doc_no", sa.String(length=64), nullable=False),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sales_order_id", sa.Integer(), sa.ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("oil_product_id", sa.String(length=64), nullable=False),
        sa.Column("warehouse_id", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ticket_no", sa.String(length=64), nullable=True),
        sa.Column("manual_ref_no", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("actual_qty", sa.Numeric(18, 3), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'草稿'")),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("submitted_by", sa.String(length=64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("doc_no", name="uq_outbound_doc_no"),
        sa.UniqueConstraint("idempotency_key", name="uq_outbound_doc_idempotency_key"),
    )
    op.create_index("ix_outbound_docs_doc_no", "outbound_docs", ["doc_no"])
    op.create_index("ix_outbound_docs_contract_id", "outbound_docs", ["contract_id"])
    op.create_index("ix_outbound_docs_sales_order_id", "outbound_docs", ["sales_order_id"])
    op.create_index("ix_outbound_docs_oil_product_id", "outbound_docs", ["oil_product_id"])
    op.create_index("ix_outbound_docs_warehouse_id", "outbound_docs", ["warehouse_id"])
    op.create_index("ix_outbound_docs_source_type", "outbound_docs", ["source_type"])
    op.create_index("ix_outbound_docs_source_ticket_no", "outbound_docs", ["source_ticket_no"])
    op.create_index("ix_outbound_docs_manual_ref_no", "outbound_docs", ["manual_ref_no"])
    op.create_index("ix_outbound_docs_idempotency_key", "outbound_docs", ["idempotency_key"])
    op.create_index("ix_outbound_docs_status", "outbound_docs", ["status"])

    op.create_table(
        "contract_qty_effects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contract_item_id", sa.Integer(), sa.ForeignKey("contract_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(length=32), nullable=False),
        sa.Column("doc_id", sa.Integer(), nullable=False),
        sa.Column("effect_type", sa.String(length=16), nullable=False),
        sa.Column("effect_qty", sa.Numeric(18, 3), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint(
            "contract_item_id",
            "doc_type",
            "doc_id",
            "effect_type",
            name="uq_contract_qty_effect_unique",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_contract_qty_effect_idempotency_key"),
    )
    op.create_index("ix_contract_qty_effects_contract_item_id", "contract_qty_effects", ["contract_item_id"])
    op.create_index("ix_contract_qty_effects_doc_type", "contract_qty_effects", ["doc_type"])
    op.create_index("ix_contract_qty_effects_doc_id", "contract_qty_effects", ["doc_id"])
    op.create_index("ix_contract_qty_effects_effect_type", "contract_qty_effects", ["effect_type"])
    op.create_index("ix_contract_qty_effects_idempotency_key", "contract_qty_effects", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("ix_contract_qty_effects_idempotency_key", table_name="contract_qty_effects")
    op.drop_index("ix_contract_qty_effects_effect_type", table_name="contract_qty_effects")
    op.drop_index("ix_contract_qty_effects_doc_id", table_name="contract_qty_effects")
    op.drop_index("ix_contract_qty_effects_doc_type", table_name="contract_qty_effects")
    op.drop_index("ix_contract_qty_effects_contract_item_id", table_name="contract_qty_effects")
    op.drop_table("contract_qty_effects")

    op.drop_index("ix_outbound_docs_status", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_idempotency_key", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_manual_ref_no", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_source_ticket_no", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_source_type", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_warehouse_id", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_oil_product_id", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_sales_order_id", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_contract_id", table_name="outbound_docs")
    op.drop_index("ix_outbound_docs_doc_no", table_name="outbound_docs")
    op.drop_table("outbound_docs")

    op.drop_index("ix_inbound_docs_status", table_name="inbound_docs")
    op.drop_index("ix_inbound_docs_idempotency_key", table_name="inbound_docs")
    op.drop_index("ix_inbound_docs_source_type", table_name="inbound_docs")
    op.drop_index("ix_inbound_docs_warehouse_id", table_name="inbound_docs")
    op.drop_index("ix_inbound_docs_oil_product_id", table_name="inbound_docs")
    op.drop_index("ix_inbound_docs_purchase_order_id", table_name="inbound_docs")
    op.drop_index("ix_inbound_docs_contract_id", table_name="inbound_docs")
    op.drop_index("ix_inbound_docs_doc_no", table_name="inbound_docs")
    op.drop_table("inbound_docs")
