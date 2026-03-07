from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportExportTask(Base):
    __tablename__ = "report_export_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    report_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="待处理", index=True
    )
    export_format: Mapped[str] = mapped_column(
        String(16), nullable=False, default="csv"
    )
    metric_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="v1"
    )
    filter_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    file_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_role_code: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    requested_company_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
