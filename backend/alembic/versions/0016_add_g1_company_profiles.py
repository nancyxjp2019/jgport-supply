"""新增 G1 公司主档表结构

Revision ID: 0016_add_g1_company_profiles
Revises: 0015_m8_report_recompute
Create Date: 2026-03-08 22:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0016_add_g1_company_profiles"
down_revision: str | Sequence[str] | None = "0015_m8_report_recompute"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("company_id", sa.String(length=64), primary_key=True),
        sa.Column("company_name", sa.String(length=128), nullable=False),
        sa.Column("company_type", sa.String(length=32), nullable=False),
        sa.Column("parent_company_id", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'启用'"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("remark", sa.String(length=256), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
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
        sa.ForeignKeyConstraint(["parent_company_id"], ["company_profiles.company_id"]),
    )
    op.create_index(
        "ix_company_profiles_company_name", "company_profiles", ["company_name"]
    )
    op.create_index(
        "ix_company_profiles_company_type", "company_profiles", ["company_type"]
    )
    op.create_index(
        "ix_company_profiles_parent_company_id",
        "company_profiles",
        ["parent_company_id"],
    )
    op.create_index("ix_company_profiles_status", "company_profiles", ["status"])
    op.create_index("ix_company_profiles_is_active", "company_profiles", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_company_profiles_is_active", table_name="company_profiles")
    op.drop_index("ix_company_profiles_status", table_name="company_profiles")
    op.drop_index(
        "ix_company_profiles_parent_company_id", table_name="company_profiles"
    )
    op.drop_index("ix_company_profiles_company_type", table_name="company_profiles")
    op.drop_index("ix_company_profiles_company_name", table_name="company_profiles")
    op.drop_table("company_profiles")
