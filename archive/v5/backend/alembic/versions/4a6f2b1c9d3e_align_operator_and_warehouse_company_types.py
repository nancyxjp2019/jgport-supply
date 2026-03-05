"""align operator and warehouse company types

Revision ID: 4a6f2b1c9d3e
Revises: d6b0f4658a1b
Create Date: 2026-03-02 15:50:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "4a6f2b1c9d3e"
down_revision: str | None = "d6b0f4658a1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_COMPANY_TYPE_ENUM = sa.Enum(
    "CUSTOMER",
    "SUPPLIER",
    "OPERATOR",
    "PLATFORM",
    name="companytype",
    native_enum=False,
)
EXPANDED_COMPANY_TYPE_ENUM = sa.Enum(
    "CUSTOMER",
    "SUPPLIER",
    "OPERATOR",
    "PLATFORM",
    "WAREHOUSE",
    name="companytype",
    native_enum=False,
)
NEW_COMPANY_TYPE_ENUM = sa.Enum(
    "CUSTOMER",
    "SUPPLIER",
    "OPERATOR",
    "WAREHOUSE",
    name="companytype",
    native_enum=False,
)


def upgrade() -> None:
    # 先放宽枚举约束，允许旧值和新值同时存在，便于迁移历史测试数据。
    with op.batch_alter_table("companies", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "company_type",
            existing_type=OLD_COMPANY_TYPE_ENUM,
            type_=EXPANDED_COMPANY_TYPE_ENUM,
            existing_nullable=False,
        )

    op.execute(sa.text("UPDATE companies SET company_type = 'WAREHOUSE' WHERE company_type = 'PLATFORM'"))

    # 再收敛到新的正式枚举，彻底移除 PLATFORM。
    with op.batch_alter_table("companies", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "company_type",
            existing_type=EXPANDED_COMPANY_TYPE_ENUM,
            type_=NEW_COMPANY_TYPE_ENUM,
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("companies", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "company_type",
            existing_type=NEW_COMPANY_TYPE_ENUM,
            type_=EXPANDED_COMPANY_TYPE_ENUM,
            existing_nullable=False,
        )

    op.execute(sa.text("UPDATE companies SET company_type = 'PLATFORM' WHERE company_type = 'WAREHOUSE'"))

    with op.batch_alter_table("companies", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "company_type",
            existing_type=EXPANDED_COMPANY_TYPE_ENUM,
            type_=OLD_COMPANY_TYPE_ENUM,
            existing_nullable=False,
        )
