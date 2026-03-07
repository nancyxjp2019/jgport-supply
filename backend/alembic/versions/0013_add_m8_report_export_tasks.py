"""新增 M8 导出任务中心表

Revision ID: 0013_add_m8_report_export_tasks
Revises: 0012_m8_supplier_confirm
Create Date: 2026-03-07 21:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0013_add_m8_report_export_tasks"
down_revision: str | Sequence[str] | None = "0012_m8_supplier_confirm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_export_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_code", sa.String(length=32), nullable=False),
        sa.Column("report_name", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'待处理'"),
        ),
        sa.Column(
            "export_format",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'csv'"),
        ),
        sa.Column(
            "metric_version",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'v1'"),
        ),
        sa.Column(
            "filter_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("file_name", sa.String(length=128), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("requested_role_code", sa.String(length=32), nullable=False),
        sa.Column("requested_company_id", sa.String(length=64), nullable=True),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "download_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "idempotency_key", sa.String(length=128), nullable=False, unique=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_report_export_tasks_report_code",
        "report_export_tasks",
        ["report_code"],
    )
    op.create_index(
        "ix_report_export_tasks_status",
        "report_export_tasks",
        ["status"],
    )
    op.create_index(
        "ix_report_export_tasks_requested_by",
        "report_export_tasks",
        ["requested_by"],
    )
    op.create_index(
        "ix_report_export_tasks_requested_role_code",
        "report_export_tasks",
        ["requested_role_code"],
    )
    op.create_index(
        "ix_report_export_tasks_requested_company_id",
        "report_export_tasks",
        ["requested_company_id"],
    )
    op.create_index(
        "ix_report_export_tasks_created_at",
        "report_export_tasks",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_report_export_tasks_created_at", table_name="report_export_tasks")
    op.drop_index(
        "ix_report_export_tasks_requested_company_id",
        table_name="report_export_tasks",
    )
    op.drop_index(
        "ix_report_export_tasks_requested_role_code",
        table_name="report_export_tasks",
    )
    op.drop_index(
        "ix_report_export_tasks_requested_by", table_name="report_export_tasks"
    )
    op.drop_index("ix_report_export_tasks_status", table_name="report_export_tasks")
    op.drop_index(
        "ix_report_export_tasks_report_code", table_name="report_export_tasks"
    )
    op.drop_table("report_export_tasks")
