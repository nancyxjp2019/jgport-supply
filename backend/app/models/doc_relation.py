from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocRelation(Base):
    __tablename__ = "doc_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_doc_type",
            "source_doc_id",
            "target_doc_type",
            "target_doc_id",
            "relation_type",
            name="uq_doc_relation_unique",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_doc_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_doc_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_doc_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_doc_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
