"""新增 M7 报表快照表

Revision ID: 0010_add_m7_reports
Revises: 0009_add_m6_contract_close
Create Date: 2026-03-06 18:40:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0010_add_m7_reports"
down_revision: str | Sequence[str] | None = "0009_add_m6_contract_close"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_code", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=16), nullable=False),
        sa.Column(
            "metric_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_report_snapshots_report_code", "report_snapshots", ["report_code"])
    op.create_index("ix_report_snapshots_version", "report_snapshots", ["version"])
    op.create_index("ix_report_snapshots_snapshot_time", "report_snapshots", ["snapshot_time"])


def downgrade() -> None:
    op.drop_index("ix_report_snapshots_snapshot_time", table_name="report_snapshots")
    op.drop_index("ix_report_snapshots_version", table_name="report_snapshots")
    op.drop_index("ix_report_snapshots_report_code", table_name="report_snapshots")
    op.drop_table("report_snapshots")
