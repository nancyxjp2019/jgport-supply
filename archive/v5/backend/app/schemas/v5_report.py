from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    days: int | None = Field(default=30, ge=0)
    from_date: date | None = None
    to_date: date | None = None


class ReportExportItemOut(BaseModel):
    id: int
    report_type: str
    report_name: str
    status: str
    created_at: datetime
    generated_by: int
    generated_by_name: str
    row_count: int
    download_url: str
    filters: dict[str, Any]
    field_profile: dict[str, Any]
    summary: dict[str, Any] | None


class ReportExportListOut(BaseModel):
    items: list[ReportExportItemOut]
    total: int
    limit: int
    offset: int
