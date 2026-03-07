from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    metric_version: str
    snapshot_time: datetime
    sla_status: str
    contract_execution_rate: Decimal
    actual_receipt_today: Decimal
    actual_payment_today: Decimal
    inventory_turnover_30d: Decimal
    threshold_alert_count: int
    message: str


class BoardTaskItem(BaseModel):
    biz_type: str
    biz_id: int
    title: str
    status: str
    contract_id: int | None = None
    contract_no: str | None = None
    related_order_id: int | None = None
    created_at: datetime | None = None


class BoardTasksResponse(BaseModel):
    metric_version: str
    snapshot_time: datetime
    sla_status: str
    pending_supplement_count: int
    validation_failed_count: int
    qty_done_not_closed_count: int
    pending_supplement_items: list[BoardTaskItem] = Field(default_factory=list)
    validation_failed_items: list[BoardTaskItem] = Field(default_factory=list)
    qty_done_not_closed_items: list[BoardTaskItem] = Field(default_factory=list)
    message: str


class LightReportOverviewResponse(BaseModel):
    metric_version: str
    snapshot_time: datetime
    sla_status: str
    actual_receipt_today: Decimal
    actual_payment_today: Decimal
    inbound_qty_today: Decimal
    outbound_qty_today: Decimal
    abnormal_count: int
    pending_supplement_count: int
    validation_failed_count: int
    qty_done_not_closed_count: int
    message: str


class AdminMultiDimReportRow(BaseModel):
    dimension: str
    dimension_value: str
    receipt_net_amount: Decimal
    payment_net_amount: Decimal
    net_cashflow: Decimal
    receipt_doc_count: int
    payment_doc_count: int
    pending_supplement_count: int
    refund_pending_review_count: int


class AdminMultiDimReportResponse(BaseModel):
    metric_version: str
    snapshot_time: datetime
    sla_status: str
    group_by: str
    filters: dict[str, str | None]
    total_receipt_net_amount: Decimal
    total_payment_net_amount: Decimal
    total_net_cashflow: Decimal
    rows: list[AdminMultiDimReportRow] = Field(default_factory=list)
    message: str


class AdminMultiDimExportTaskCreateRequest(BaseModel):
    metric_version: str | None = Field(default=None, max_length=16)
    group_by: str = Field(default="contract_direction")
    contract_direction: str | None = Field(default=None)
    doc_status: str | None = Field(default=None, max_length=16)
    refund_status: str | None = Field(default=None, max_length=16)
    date_from: date | None = None
    date_to: date | None = None


class AdminMultiDimExportTaskItem(BaseModel):
    id: int
    report_code: str
    report_name: str
    status: str
    export_format: str
    metric_version: str
    filters: dict[str, str | None]
    file_name: str | None = None
    requested_by: str
    requested_role_code: str
    requested_company_id: str | None = None
    retry_count: int
    download_count: int
    error_message: str | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminMultiDimExportTaskCreateResponse(BaseModel):
    task: AdminMultiDimExportTaskItem
    message: str


class AdminMultiDimExportTaskListResponse(BaseModel):
    items: list[AdminMultiDimExportTaskItem] = Field(default_factory=list)
    message: str
