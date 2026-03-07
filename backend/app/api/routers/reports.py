from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, require_actor
from app.db.session import get_db
from app.schemas.report import (
    AdminMultiDimReportResponse,
    AdminMultiDimReportRow,
    BoardTaskItem,
    BoardTasksResponse,
    DashboardSummaryResponse,
    LightReportOverviewResponse,
)
from app.services.report_service import (
    ReportServiceError,
    build_admin_multi_dim_report_csv,
    get_admin_multi_dim_report,
    get_board_tasks,
    get_dashboard_summary,
    get_light_overview,
)

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
    metric_version: str | None = Query(
        default=None, max_length=16, description="指标口径版本"
    ),
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
    metric_version: str | None = Query(
        default=None, max_length=16, description="指标口径版本"
    ),
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
        pending_supplement_items=[
            BoardTaskItem(**item) for item in result.payload["pending_supplement_items"]
        ],
        validation_failed_items=[
            BoardTaskItem(**item) for item in result.payload["validation_failed_items"]
        ],
        qty_done_not_closed_items=[
            BoardTaskItem(**item)
            for item in result.payload["qty_done_not_closed_items"]
        ],
        message="业务看板查询成功",
    )


@router.get("/reports/light/overview", response_model=LightReportOverviewResponse)
def get_light_overview_route(
    metric_version: str | None = Query(
        default=None, max_length=16, description="指标口径版本"
    ),
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


@router.get("/reports/admin/multi-dim", response_model=AdminMultiDimReportResponse)
def get_admin_multi_dim_route(
    metric_version: str | None = Query(
        default=None, max_length=16, description="指标口径版本"
    ),
    group_by: str = Query(
        default="contract_direction",
        pattern="^(contract_direction|doc_status|refund_status)$",
        description="多维分组方式",
    ),
    contract_direction: str | None = Query(
        default=None,
        pattern="^(sales|purchase)$",
        description="合同方向筛选",
    ),
    doc_status: str | None = Query(
        default=None, max_length=16, description="单据状态筛选"
    ),
    refund_status: str | None = Query(
        default=None,
        max_length=16,
        description="退款状态筛选",
    ),
    date_from: date | None = Query(
        default=None, description="创建日期起始（上海自然日）"
    ),
    date_to: date | None = Query(
        default=None, description="创建日期结束（上海自然日）"
    ),
    _: AuthenticatedActor = Depends(admin_report_dependency),
    db: Session = Depends(get_db),
) -> AdminMultiDimReportResponse:
    try:
        result = get_admin_multi_dim_report(
            db,
            metric_version=metric_version,
            group_by=group_by,
            contract_direction=contract_direction,
            doc_status=doc_status,
            refund_status=refund_status,
            date_from=date_from,
            date_to=date_to,
        )
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return AdminMultiDimReportResponse(
        metric_version=result.metric_version,
        snapshot_time=result.snapshot_time,
        sla_status=result.sla_status,
        group_by=result.group_by,
        filters=result.filters,
        total_receipt_net_amount=result.total_receipt_net_amount,
        total_payment_net_amount=result.total_payment_net_amount,
        total_net_cashflow=result.total_net_cashflow,
        rows=[AdminMultiDimReportRow(**row.__dict__) for row in result.rows],
        message="后台多维报表查询成功",
    )


@router.get("/reports/admin/multi-dim/export")
def export_admin_multi_dim_route(
    metric_version: str | None = Query(
        default=None, max_length=16, description="指标口径版本"
    ),
    group_by: str = Query(
        default="contract_direction",
        pattern="^(contract_direction|doc_status|refund_status)$",
        description="多维分组方式",
    ),
    contract_direction: str | None = Query(
        default=None,
        pattern="^(sales|purchase)$",
        description="合同方向筛选",
    ),
    doc_status: str | None = Query(
        default=None, max_length=16, description="单据状态筛选"
    ),
    refund_status: str | None = Query(
        default=None,
        max_length=16,
        description="退款状态筛选",
    ),
    date_from: date | None = Query(
        default=None, description="创建日期起始（上海自然日）"
    ),
    date_to: date | None = Query(
        default=None, description="创建日期结束（上海自然日）"
    ),
    _: AuthenticatedActor = Depends(admin_report_dependency),
    db: Session = Depends(get_db),
) -> Response:
    try:
        result = get_admin_multi_dim_report(
            db,
            metric_version=metric_version,
            group_by=group_by,
            contract_direction=contract_direction,
            doc_status=doc_status,
            refund_status=refund_status,
            date_from=date_from,
            date_to=date_to,
        )
        csv_content = build_admin_multi_dim_report_csv(result)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    file_suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="multi-dim-report-{file_suffix}.csv"'
        },
    )
