"""add supplier role and review stage

Revision ID: c3f8a1b2d4e5
Revises: 4c8f3d9b2a1e
Create Date: 2026-02-28 16:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c3f8a1b2d4e5"
down_revision: str | None = "4c8f3d9b2a1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD_USER_ROLE_ENUM = sa.Enum(
    "ADMIN",
    "OPERATOR",
    "FINANCE",
    "CUSTOMER",
    "WAREHOUSE",
    name="userrole",
    native_enum=False,
)

_NEW_USER_ROLE_ENUM = sa.Enum(
    "ADMIN",
    "OPERATOR",
    "FINANCE",
    "SUPPLIER",
    "CUSTOMER",
    "WAREHOUSE",
    name="userrole",
    native_enum=False,
)

_OLD_ORDER_STATUS_ENUM = sa.Enum(
    "SUBMITTED",
    "ACCEPTED",
    "REJECTED",
    "PAID_PENDING_CONFIRM",
    "PAID_CONFIRMED",
    "DISPATCHED",
    "COMPLETED",
    "CANCELLED",
    "ABNORMAL_CLOSED",
    name="orderstatus",
    native_enum=False,
)

_NEW_ORDER_STATUS_ENUM = sa.Enum(
    "SUBMITTED",
    "ACCEPTED",
    "REJECTED",
    "PAID_PENDING_CONFIRM",
    "PAID_CONFIRMED",
    "SUPPLIER_CONFIRMED",
    "DISPATCHED",
    "COMPLETED",
    "CANCELLED",
    "ABNORMAL_CLOSED",
    name="orderstatus",
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
        batch_op.alter_column(
            "status",
            existing_type=_OLD_ORDER_STATUS_ENUM,
            type_=_NEW_ORDER_STATUS_ENUM,
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column("supplier_dispatch_doc_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'FINANCE' WHERE role = 'SUPPLIER'")
    op.execute("UPDATE orders SET status = 'PAID_CONFIRMED' WHERE status = 'SUPPLIER_CONFIRMED'")

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("supplier_dispatch_doc_url")
        batch_op.alter_column(
            "status",
            existing_type=_NEW_ORDER_STATUS_ENUM,
            type_=_OLD_ORDER_STATUS_ENUM,
            existing_nullable=False,
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=_NEW_USER_ROLE_ENUM,
            type_=_OLD_USER_ROLE_ENUM,
            existing_nullable=False,
        )
