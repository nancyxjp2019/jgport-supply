from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, require_actor
from app.db.session import get_db
from app.schemas.report import (
    AdminMultiDimExportTaskCreateRequest,
    AdminMultiDimExportTaskCreateResponse,
    AdminMultiDimExportTaskItem,
    AdminMultiDimExportTaskListResponse,
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
    create_admin_multi_dim_export_task,
    execute_admin_multi_dim_export_task,
    get_admin_multi_dim_report,
    get_board_tasks,
    get_dashboard_summary,
    get_light_overview,
    list_admin_multi_dim_export_tasks,
    prepare_admin_multi_dim_export_task_download,
    retry_admin_multi_dim_export_task,
)

router = APIRouter(tags=["reports"])

admin_report_dependency = require_actor(
    allowed_roles={"operations", "finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)
admin_report_export_dependency = require_actor(
    allowed_roles={"finance", "admin"},
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
    _: AuthenticatedActor = Depends(admin_report_export_dependency),
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


@router.post(
    "/reports/admin/multi-dim/export-tasks",
    response_model=AdminMultiDimExportTaskCreateResponse,
    status_code=202,
)
def create_admin_multi_dim_export_task_route(
    payload: AdminMultiDimExportTaskCreateRequest,
    background_tasks: BackgroundTasks,
    actor: AuthenticatedActor = Depends(admin_report_export_dependency),
    db: Session = Depends(get_db),
) -> AdminMultiDimExportTaskCreateResponse:
    try:
        dispatch_result = create_admin_multi_dim_export_task(
            db,
            actor=actor,
            metric_version=payload.metric_version,
            group_by=payload.group_by,
            contract_direction=payload.contract_direction,
            doc_status=payload.doc_status,
            refund_status=payload.refund_status,
            date_from=payload.date_from,
            date_to=payload.date_to,
        )
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if dispatch_result.should_enqueue:
        background_tasks.add_task(
            execute_admin_multi_dim_export_task, dispatch_result.task.id
        )
    return AdminMultiDimExportTaskCreateResponse(
        task=AdminMultiDimExportTaskItem(**dispatch_result.task.__dict__),
        message=(
            "导出任务已创建，正在后台生成文件"
            if dispatch_result.should_enqueue
            else "命中相同筛选快照的未完成任务，已直接复用现有任务"
        ),
    )


@router.get(
    "/reports/admin/multi-dim/export-tasks",
    response_model=AdminMultiDimExportTaskListResponse,
)
def list_admin_multi_dim_export_tasks_route(
    limit: int = Query(default=20, ge=1, le=100, description="返回条数上限"),
    task_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(待处理|处理中|已完成|已失败)$",
        description="任务状态筛选",
    ),
    actor: AuthenticatedActor = Depends(admin_report_export_dependency),
    db: Session = Depends(get_db),
) -> AdminMultiDimExportTaskListResponse:
    try:
        items = list_admin_multi_dim_export_tasks(
            db,
            actor=actor,
            limit=limit,
            task_status=task_status,
        )
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return AdminMultiDimExportTaskListResponse(
        items=[AdminMultiDimExportTaskItem(**item.__dict__) for item in items],
        message="导出任务列表查询成功",
    )


@router.get("/reports/admin/multi-dim/export-tasks/{task_id}/download")
def download_admin_multi_dim_export_task_route(
    task_id: int,
    actor: AuthenticatedActor = Depends(admin_report_export_dependency),
    db: Session = Depends(get_db),
) -> FileResponse:
    try:
        result = prepare_admin_multi_dim_export_task_download(
            db,
            actor=actor,
            task_id=task_id,
        )
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return FileResponse(
        path=result.file_path,
        media_type="text/csv",
        filename=result.file_name,
    )


@router.post(
    "/reports/admin/multi-dim/export-tasks/{task_id}/retry",
    response_model=AdminMultiDimExportTaskCreateResponse,
    status_code=202,
)
def retry_admin_multi_dim_export_task_route(
    task_id: int,
    background_tasks: BackgroundTasks,
    actor: AuthenticatedActor = Depends(admin_report_export_dependency),
    db: Session = Depends(get_db),
) -> AdminMultiDimExportTaskCreateResponse:
    try:
        task = retry_admin_multi_dim_export_task(db, actor=actor, task_id=task_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    background_tasks.add_task(execute_admin_multi_dim_export_task, task.id)
    return AdminMultiDimExportTaskCreateResponse(
        task=AdminMultiDimExportTaskItem(**task.__dict__),
        message="导出任务已重新发起，正在后台生成文件",
    )
