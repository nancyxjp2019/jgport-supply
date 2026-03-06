"""新增 M4 第二批凭证附件表

Revision ID: 0007_add_m4_doc_attach
Revises: 0006_add_m4_funds_domain
Create Date: 2026-03-06 22:10:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_add_m4_doc_attach"
down_revision: str | Sequence[str] | None = "0006_add_m4_funds_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doc_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_doc_type", sa.String(length=32), nullable=False),
        sa.Column("owner_doc_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("biz_tag", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint(
            "owner_doc_type",
            "owner_doc_id",
            "path",
            "biz_tag",
            name="uq_doc_attachment_unique",
        ),
    )
    op.create_index("ix_doc_attachments_owner_doc_type", "doc_attachments", ["owner_doc_type"])
    op.create_index("ix_doc_attachments_owner_doc_id", "doc_attachments", ["owner_doc_id"])
    op.create_index("ix_doc_attachments_biz_tag", "doc_attachments", ["biz_tag"])


def downgrade() -> None:
    op.drop_index("ix_doc_attachments_biz_tag", table_name="doc_attachments")
    op.drop_index("ix_doc_attachments_owner_doc_id", table_name="doc_attachments")
    op.drop_index("ix_doc_attachments_owner_doc_type", table_name="doc_attachments")
    op.drop_table("doc_attachments")
