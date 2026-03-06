from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocAttachment(Base):
    __tablename__ = "doc_attachments"
    __table_args__ = (
        UniqueConstraint(
            "owner_doc_type",
            "owner_doc_id",
            "path",
            "biz_tag",
            name="uq_doc_attachment_unique",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_doc_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    owner_doc_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    biz_tag: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
