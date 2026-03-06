from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    metric_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
