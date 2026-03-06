"""修复 M1 评审问题

Revision ID: 0003_fix_m1_review_findings
Revises: 0002_add_m1_foundation
Create Date: 2026-03-06 14:10:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_fix_m1_review_findings"
down_revision: str | Sequence[str] | None = "0002_add_m1_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "role_company_bindings",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.drop_constraint("uq_role_company_binding", "role_company_bindings", type_="unique")
    op.create_unique_constraint(
        "uq_role_company_binding_version",
        "role_company_bindings",
        ["role_code", "company_type", "version"],
    )
    op.create_index(
        "uq_role_company_binding_active",
        "role_company_bindings",
        ["role_code", "company_type"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_role_company_binding_active", table_name="role_company_bindings")
    op.drop_constraint("uq_role_company_binding_version", "role_company_bindings", type_="unique")
    op.create_unique_constraint(
        "uq_role_company_binding",
        "role_company_bindings",
        ["role_code", "company_type"],
    )
    op.drop_column("role_company_bindings", "is_active")
