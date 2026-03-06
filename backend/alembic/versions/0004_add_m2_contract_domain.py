"""新增 M2 合同域表结构

Revision ID: 0004_add_m2_contract_domain
Revises: 0003_fix_m1_review_findings
Create Date: 2026-03-06 19:10:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_add_m2_contract_domain"
down_revision: str | Sequence[str] | None = "0003_fix_m1_review_findings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contract_no", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'草稿'")),
        sa.Column("supplier_id", sa.String(length=64), nullable=True),
        sa.Column("customer_id", sa.String(length=64), nullable=True),
        sa.Column("threshold_release_snapshot", sa.Numeric(8, 3), nullable=True),
        sa.Column("threshold_over_exec_snapshot", sa.Numeric(8, 3), nullable=True),
        sa.Column("close_type", sa.String(length=16), nullable=True),
        sa.Column("manual_close_reason", sa.String(length=256), nullable=True),
        sa.Column("submit_comment", sa.String(length=256), nullable=True),
        sa.Column("approval_comment", sa.String(length=256), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.Column("approved_by", sa.String(length=64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("contract_no", name="uq_contract_no"),
    )
    op.create_index("ix_contracts_contract_no", "contracts", ["contract_no"])
    op.create_index("ix_contracts_direction", "contracts", ["direction"])
    op.create_index("ix_contracts_status", "contracts", ["status"])
    op.create_index("ix_contracts_supplier_id", "contracts", ["supplier_id"])
    op.create_index("ix_contracts_customer_id", "contracts", ["customer_id"])

    op.create_table(
        "contract_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("oil_product_id", sa.String(length=64), nullable=False),
        sa.Column("qty_signed", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("qty_in_acc", sa.Numeric(18, 3), nullable=False, server_default=sa.text("0")),
        sa.Column("qty_out_acc", sa.Numeric(18, 3), nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("contract_id", "oil_product_id", name="uq_contract_item_oil_product"),
    )
    op.create_index("ix_contract_items_contract_id", "contract_items", ["contract_id"])

    op.create_table(
        "contract_effective_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_doc_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'待处理'")),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("idempotency_key", name="uq_contract_effective_task_key"),
    )
    op.create_index("ix_contract_effective_tasks_contract_id", "contract_effective_tasks", ["contract_id"])
    op.create_index("ix_contract_effective_tasks_target_doc_type", "contract_effective_tasks", ["target_doc_type"])
    op.create_index("ix_contract_effective_tasks_status", "contract_effective_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_contract_effective_tasks_status", table_name="contract_effective_tasks")
    op.drop_index("ix_contract_effective_tasks_target_doc_type", table_name="contract_effective_tasks")
    op.drop_index("ix_contract_effective_tasks_contract_id", table_name="contract_effective_tasks")
    op.drop_table("contract_effective_tasks")

    op.drop_index("ix_contract_items_contract_id", table_name="contract_items")
    op.drop_table("contract_items")

    op.drop_index("ix_contracts_customer_id", table_name="contracts")
    op.drop_index("ix_contracts_supplier_id", table_name="contracts")
    op.drop_index("ix_contracts_status", table_name="contracts")
    op.drop_index("ix_contracts_direction", table_name="contracts")
    op.drop_index("ix_contracts_contract_no", table_name="contracts")
    op.drop_table("contracts")
