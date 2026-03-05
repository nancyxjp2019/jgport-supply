"""add finance role and order fields

Revision ID: 9a2c8f6d1b3e
Revises: 7d5f54c17f2a
Create Date: 2026-02-11 23:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "9a2c8f6d1b3e"
down_revision: str | None = "7d5f54c17f2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD_USER_ROLE_ENUM = sa.Enum(
    "ADMIN",
    "OPERATOR",
    "CUSTOMER",
    "WAREHOUSE",
    name="userrole",
    native_enum=False,
)

_NEW_USER_ROLE_ENUM = sa.Enum(
    "ADMIN",
    "OPERATOR",
    "FINANCE",
    "CUSTOMER",
    "WAREHOUSE",
    name="userrole",
    native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=_OLD_USER_ROLE_ENUM,
            type_=_NEW_USER_ROLE_ENUM,
            existing_nullable=False,
        )

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(sa.Column("finance_received_amount", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("pickup_instruction_pdf_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("pickup_instruction_pdf_url")
        batch_op.drop_column("finance_received_amount")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=_NEW_USER_ROLE_ENUM,
            type_=_OLD_USER_ROLE_ENUM,
            existing_nullable=False,
        )
