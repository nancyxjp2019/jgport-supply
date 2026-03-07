"""新增 M8 日报扫描幂等索引

Revision ID: 0014_m8_daily_scan_idx
Revises: 0013_add_m8_report_export_tasks
Create Date: 2026-03-07 23:40:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0014_m8_daily_scan_idx"
down_revision: str | Sequence[str] | None = "0013_add_m8_report_export_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_business_audit_logs_daily_scan_state
        ON business_audit_logs (biz_type, biz_id)
        WHERE biz_type = 'report_daily_contract_scan_state'
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_business_audit_logs_daily_scan_result
        ON business_audit_logs (biz_type, biz_id)
        WHERE biz_type = 'report_daily_contract_scan'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_business_audit_logs_daily_scan_result")
    op.execute("DROP INDEX IF EXISTS uq_business_audit_logs_daily_scan_state")
