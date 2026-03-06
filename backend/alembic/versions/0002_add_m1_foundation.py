"""新增 M1 基础能力表结构

Revision ID: 0002_add_m1_foundation
Revises: 0001_init_v6_schema
Create Date: 2026-03-06 11:20:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_add_m1_foundation"
down_revision: str | Sequence[str] | None = "0001_init_v6_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "role_company_bindings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role_code", sa.String(length=32), nullable=False),
        sa.Column("company_type", sa.String(length=32), nullable=False),
        sa.Column("admin_web_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("miniprogram_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'生效'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("role_code", "company_type", name="uq_role_company_binding"),
    )
    op.create_index("ix_role_company_bindings_role_code", "role_company_bindings", ["role_code"])
    op.create_index("ix_role_company_bindings_company_type", "role_company_bindings", ["company_type"])

    op.create_table(
        "threshold_config_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("version", sa.Integer(), nullable=False, unique=True),
        sa.Column("threshold_release", sa.Numeric(8, 3), nullable=False),
        sa.Column("threshold_over_exec", sa.Numeric(8, 3), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'生效'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_threshold_config_versions_is_active", "threshold_config_versions", ["is_active"])

    op.create_table(
        "business_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_code", sa.String(length=64), nullable=False),
        sa.Column("biz_type", sa.String(length=64), nullable=False),
        sa.Column("biz_id", sa.String(length=64), nullable=False),
        sa.Column("operator_id", sa.String(length=64), nullable=False),
        sa.Column("before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("extra_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_business_audit_logs_event_code", "business_audit_logs", ["event_code"])
    op.create_index("ix_business_audit_logs_biz_type", "business_audit_logs", ["biz_type"])
    op.create_index("ix_business_audit_logs_biz_id", "business_audit_logs", ["biz_id"])
    op.create_index("ix_business_audit_logs_operator_id", "business_audit_logs", ["operator_id"])

    role_company_bindings_table = sa.table(
        "role_company_bindings",
        sa.column("role_code", sa.String),
        sa.column("company_type", sa.String),
        sa.column("admin_web_allowed", sa.Boolean),
        sa.column("miniprogram_allowed", sa.Boolean),
        sa.column("status", sa.String),
        sa.column("version", sa.Integer),
    )
    op.bulk_insert(
        role_company_bindings_table,
        [
            {
                "role_code": "customer",
                "company_type": "customer_company",
                "admin_web_allowed": False,
                "miniprogram_allowed": True,
                "status": "生效",
                "version": 1,
            },
            {
                "role_code": "supplier",
                "company_type": "supplier_company",
                "admin_web_allowed": False,
                "miniprogram_allowed": True,
                "status": "生效",
                "version": 1,
            },
            {
                "role_code": "warehouse",
                "company_type": "warehouse_company",
                "admin_web_allowed": False,
                "miniprogram_allowed": True,
                "status": "生效",
                "version": 1,
            },
            {
                "role_code": "operations",
                "company_type": "operator_company",
                "admin_web_allowed": True,
                "miniprogram_allowed": True,
                "status": "生效",
                "version": 1,
            },
            {
                "role_code": "finance",
                "company_type": "operator_company",
                "admin_web_allowed": True,
                "miniprogram_allowed": True,
                "status": "生效",
                "version": 1,
            },
            {
                "role_code": "admin",
                "company_type": "operator_company",
                "admin_web_allowed": True,
                "miniprogram_allowed": True,
                "status": "生效",
                "version": 1,
            },
        ],
    )

    threshold_config_versions_table = sa.table(
        "threshold_config_versions",
        sa.column("version", sa.Integer),
        sa.column("threshold_release", sa.Numeric),
        sa.column("threshold_over_exec", sa.Numeric),
        sa.column("status", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("reason", sa.String),
        sa.column("created_by", sa.String),
    )
    op.bulk_insert(
        threshold_config_versions_table,
        [
            {
                "version": 1,
                "threshold_release": 1.050,
                "threshold_over_exec": 1.050,
                "status": "生效",
                "is_active": True,
                "reason": "系统初始化默认值",
                "created_by": "system",
            }
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_business_audit_logs_operator_id", table_name="business_audit_logs")
    op.drop_index("ix_business_audit_logs_biz_id", table_name="business_audit_logs")
    op.drop_index("ix_business_audit_logs_biz_type", table_name="business_audit_logs")
    op.drop_index("ix_business_audit_logs_event_code", table_name="business_audit_logs")
    op.drop_table("business_audit_logs")

    op.drop_index("ix_threshold_config_versions_is_active", table_name="threshold_config_versions")
    op.drop_table("threshold_config_versions")

    op.drop_index("ix_role_company_bindings_company_type", table_name="role_company_bindings")
    op.drop_index("ix_role_company_bindings_role_code", table_name="role_company_bindings")
    op.drop_table("role_company_bindings")
