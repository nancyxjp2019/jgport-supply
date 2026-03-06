from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, require_actor
from app.db.session import get_db
from app.schemas.report import BoardTaskItem, BoardTasksResponse, DashboardSummaryResponse, LightReportOverviewResponse
from app.services.report_service import ReportServiceError, get_board_tasks, get_dashboard_summary, get_light_overview

router = APIRouter(tags=["reports"])

admin_report_dependency = require_actor(
    allowed_roles={"operations", "finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)
mini_report_dependency = require_actor(
    allowed_roles={"operations", "finance", "admin"},
    allowed_client_types={"miniprogram"},
    allowed_company_types={"operator_company"},
)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary_route(
    metric_version: str | None = Query(default=None, max_length=16, description="指标口径版本"),
    _: AuthenticatedActor = Depends(admin_report_dependency),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    try:
        result = get_dashboard_summary(db, metric_version=metric_version)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return DashboardSummaryResponse(
        metric_version=result.metric_version,
        snapshot_time=result.snapshot_time,
        sla_status=result.sla_status,
        contract_execution_rate=Decimal(result.payload["contract_execution_rate"]),
        actual_receipt_today=Decimal(result.payload["actual_receipt_today"]),
        actual_payment_today=Decimal(result.payload["actual_payment_today"]),
        inventory_turnover_30d=Decimal(result.payload["inventory_turnover_30d"]),
        threshold_alert_count=int(result.payload["threshold_alert_count"]),
        message="仪表盘查询成功",
    )


@router.get("/boards/tasks", response_model=BoardTasksResponse)
def get_board_tasks_route(
    metric_version: str | None = Query(default=None, max_length=16, description="指标口径版本"),
    _: AuthenticatedActor = Depends(admin_report_dependency),
    db: Session = Depends(get_db),
) -> BoardTasksResponse:
    try:
        result = get_board_tasks(db, metric_version=metric_version)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return BoardTasksResponse(
        metric_version=result.metric_version,
        snapshot_time=result.snapshot_time,
        sla_status=result.sla_status,
        pending_supplement_count=int(result.payload["pending_supplement_count"]),
        validation_failed_count=int(result.payload["validation_failed_count"]),
        qty_done_not_closed_count=int(result.payload["qty_done_not_closed_count"]),
        pending_supplement_items=[BoardTaskItem(**item) for item in result.payload["pending_supplement_items"]],
        validation_failed_items=[BoardTaskItem(**item) for item in result.payload["validation_failed_items"]],
        qty_done_not_closed_items=[BoardTaskItem(**item) for item in result.payload["qty_done_not_closed_items"]],
        message="业务看板查询成功",
    )


@router.get("/reports/light/overview", response_model=LightReportOverviewResponse)
def get_light_overview_route(
    metric_version: str | None = Query(default=None, max_length=16, description="指标口径版本"),
    _: AuthenticatedActor = Depends(mini_report_dependency),
    db: Session = Depends(get_db),
) -> LightReportOverviewResponse:
    try:
        result = get_light_overview(db, metric_version=metric_version)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return LightReportOverviewResponse(
        metric_version=result.metric_version,
        snapshot_time=result.snapshot_time,
        sla_status=result.sla_status,
        actual_receipt_today=Decimal(result.payload["actual_receipt_today"]),
        actual_payment_today=Decimal(result.payload["actual_payment_today"]),
        inbound_qty_today=Decimal(result.payload["inbound_qty_today"]),
        outbound_qty_today=Decimal(result.payload["outbound_qty_today"]),
        abnormal_count=int(result.payload["abnormal_count"]),
        pending_supplement_count=int(result.payload["pending_supplement_count"]),
        validation_failed_count=int(result.payload["validation_failed_count"]),
        qty_done_not_closed_count=int(result.payload["qty_done_not_closed_count"]),
        message="轻量报表查询成功",
    )


@router.get("/reports/admin/multi-dim")
def get_admin_multi_dim_route(
    _: AuthenticatedActor = Depends(admin_report_dependency),
) -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="后台多维报表尚未纳入 M7 首批实现",
    )
