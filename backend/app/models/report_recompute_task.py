from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportRecomputeTask(Base):
    __tablename__ = "report_recompute_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="待处理", index=True
    )
    metric_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="v1"
    )
    report_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    result_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    requested_by: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_role_code: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    requested_company_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
