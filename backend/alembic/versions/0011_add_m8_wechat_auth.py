"""新增 M8 微信登录绑定表

Revision ID: 0011_add_m8_wechat_auth
Revises: 0010_add_m7_reports
Create Date: 2026-03-06 23:30:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0011_add_m8_wechat_auth"
down_revision: str | Sequence[str] | None = "0010_add_m7_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mini_program_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("openid", sa.String(length=80), nullable=False),
        sa.Column("unionid", sa.String(length=80), nullable=True),
        sa.Column("role_code", sa.String(length=32), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("company_type", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="生效"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_mini_program_accounts_openid", "mini_program_accounts", ["openid"], unique=True)
    op.create_index("ix_mini_program_accounts_unionid", "mini_program_accounts", ["unionid"], unique=False)
    op.create_index("ix_mini_program_accounts_role_code", "mini_program_accounts", ["role_code"], unique=False)
    op.create_index("ix_mini_program_accounts_company_id", "mini_program_accounts", ["company_id"], unique=False)
    op.create_index("ix_mini_program_accounts_company_type", "mini_program_accounts", ["company_type"], unique=False)
    op.create_index("ix_mini_program_accounts_status", "mini_program_accounts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mini_program_accounts_status", table_name="mini_program_accounts")
    op.drop_index("ix_mini_program_accounts_company_type", table_name="mini_program_accounts")
    op.drop_index("ix_mini_program_accounts_company_id", table_name="mini_program_accounts")
    op.drop_index("ix_mini_program_accounts_role_code", table_name="mini_program_accounts")
    op.drop_index("ix_mini_program_accounts_unionid", table_name="mini_program_accounts")
    op.drop_index("ix_mini_program_accounts_openid", table_name="mini_program_accounts")
    op.drop_table("mini_program_accounts")
