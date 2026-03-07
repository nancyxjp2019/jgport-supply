"""新增 M8 汇总报表重算任务表

Revision ID: 0015_m8_report_recompute
Revises: 0014_m8_daily_scan_idx
Create Date: 2026-03-08 00:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0015_m8_report_recompute"
down_revision: str | Sequence[str] | None = "0014_m8_daily_scan_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_recompute_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_name", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'待处理'"),
        ),
        sa.Column(
            "metric_version",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'v1'"),
        ),
        sa.Column(
            "report_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column(
            "result_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("requested_role_code", sa.String(length=32), nullable=False),
        sa.Column("requested_company_id", sa.String(length=64), nullable=True),
        sa.Column(
            "retry_count",
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
        "ix_report_recompute_tasks_status",
        "report_recompute_tasks",
        ["status"],
    )
    op.create_index(
        "ix_report_recompute_tasks_requested_by",
        "report_recompute_tasks",
        ["requested_by"],
    )
    op.create_index(
        "ix_report_recompute_tasks_requested_role_code",
        "report_recompute_tasks",
        ["requested_role_code"],
    )
    op.create_index(
        "ix_report_recompute_tasks_requested_company_id",
        "report_recompute_tasks",
        ["requested_company_id"],
    )
    op.create_index(
        "ix_report_recompute_tasks_created_at",
        "report_recompute_tasks",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_recompute_tasks_created_at",
        table_name="report_recompute_tasks",
    )
    op.drop_index(
        "ix_report_recompute_tasks_requested_company_id",
        table_name="report_recompute_tasks",
    )
    op.drop_index(
        "ix_report_recompute_tasks_requested_role_code",
        table_name="report_recompute_tasks",
    )
    op.drop_index(
        "ix_report_recompute_tasks_requested_by",
        table_name="report_recompute_tasks",
    )
    op.drop_index(
        "ix_report_recompute_tasks_status",
        table_name="report_recompute_tasks",
    )
    op.drop_table("report_recompute_tasks")
