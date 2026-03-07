from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth_actor import AuthenticatedActor
from app.db.session import SessionLocal
from app.models.business_audit_log import BusinessAuditLog
from app.models.report_recompute_task import ReportRecomputeTask
from app.models.report_snapshot import ReportSnapshot
from app.services.report_service import (
    METRIC_VERSION_V1,
    REPORT_CODE_BOARD,
    REPORT_CODE_DASHBOARD,
    REPORT_CODE_LIGHT,
    ReportServiceError,
    _build_board_payload,
    _build_dashboard_payload,
    _build_light_payload,
    _ensure_daily_contract_scan,
    _resolve_metric_version,
)

REPORT_RECOMPUTE_TASK_NAME = "汇总报表口径重算"
RECOMPUTE_STATUS_PENDING = "待处理"
RECOMPUTE_STATUS_PROCESSING = "处理中"
RECOMPUTE_STATUS_COMPLETED = "已完成"
RECOMPUTE_STATUS_FAILED = "已失败"
RECOMPUTE_STATUS_SCOPE = {
    RECOMPUTE_STATUS_PENDING,
    RECOMPUTE_STATUS_PROCESSING,
    RECOMPUTE_STATUS_COMPLETED,
    RECOMPUTE_STATUS_FAILED,
}
REPORT_RECOMPUTE_AUDIT_CREATE = "REPORT_RECOMPUTE_TASK_CREATED"
REPORT_RECOMPUTE_AUDIT_PROCESSING = "REPORT_RECOMPUTE_TASK_PROCESSING"
REPORT_RECOMPUTE_AUDIT_COMPLETED = "REPORT_RECOMPUTE_TASK_COMPLETED"
REPORT_RECOMPUTE_AUDIT_FAILED = "REPORT_RECOMPUTE_TASK_FAILED"
REPORT_RECOMPUTE_AUDIT_RETRIED = "REPORT_RECOMPUTE_TASK_RETRIED"
REPORT_RECOMPUTE_BIZ_TYPE = "report_recompute_task"
RECOMPUTE_TRIGGER_SOURCE = "manual_recompute_task"
SUMMARY_REPORT_CODE_SCOPE = [
    REPORT_CODE_DASHBOARD,
    REPORT_CODE_BOARD,
    REPORT_CODE_LIGHT,
]
SUMMARY_REPORT_LABELS = {
    REPORT_CODE_DASHBOARD: "经营仪表盘",
    REPORT_CODE_BOARD: "业务看板",
    REPORT_CODE_LIGHT: "轻量报表",
}


@dataclass(frozen=True)
class ReportRecomputeTaskResult:
    id: int
    task_name: str
    status: str
    metric_version: str
    report_codes: list[str]
    reason: str
    requested_by: str
    requested_role_code: str
    requested_company_id: str | None
    retry_count: int
    error_message: str | None
    result_payload: dict[str, dict[str, str]]
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ReportRecomputeTaskDispatchResult:
    task: ReportRecomputeTaskResult
    should_enqueue: bool


def create_summary_report_recompute_task(
    db: Session,
    *,
    actor: AuthenticatedActor,
    metric_version: str | None,
    report_codes: list[str],
    reason: str,
) -> ReportRecomputeTaskDispatchResult:
    version = _resolve_metric_version(metric_version)
    normalized_codes = _normalize_summary_report_codes(report_codes)
    normalized_reason = _normalize_recompute_reason(reason)
    request_fingerprint = _build_recompute_request_fingerprint(
        requested_by=actor.user_id,
        requested_company_id=actor.company_id,
        metric_version=version,
        report_codes=normalized_codes,
        reason=normalized_reason,
    )
    existing_task = _find_in_progress_report_recompute_task(
        db,
        request_fingerprint=request_fingerprint,
    )
    if existing_task is not None:
        return ReportRecomputeTaskDispatchResult(
            task=_serialize_report_recompute_task(existing_task),
            should_enqueue=False,
        )

    task = ReportRecomputeTask(
        task_name=REPORT_RECOMPUTE_TASK_NAME,
        status=RECOMPUTE_STATUS_PENDING,
        metric_version=version,
        report_codes=normalized_codes,
        reason=normalized_reason,
        requested_by=actor.user_id,
        requested_role_code=actor.role_code,
        requested_company_id=actor.company_id,
        idempotency_key=request_fingerprint,
    )
    try:
        db.add(task)
        db.flush()
        _append_report_recompute_audit_log(
            db,
            task=task,
            event_code=REPORT_RECOMPUTE_AUDIT_CREATE,
            operator_id=actor.user_id,
            before_payload={},
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        existing_task = _find_in_progress_report_recompute_task(
            db,
            request_fingerprint=request_fingerprint,
        )
        if existing_task is not None:
            return ReportRecomputeTaskDispatchResult(
                task=_serialize_report_recompute_task(existing_task),
                should_enqueue=False,
            )
        raise ReportServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重算任务创建失败，请稍后重试",
        )
    db.refresh(task)
    return ReportRecomputeTaskDispatchResult(
        task=_serialize_report_recompute_task(task),
        should_enqueue=True,
    )


def list_summary_report_recompute_tasks(
    db: Session,
    *,
    actor: AuthenticatedActor,
    limit: int,
    task_status: str | None,
) -> list[ReportRecomputeTaskResult]:
    if task_status and task_status not in RECOMPUTE_STATUS_SCOPE:
        raise ReportServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="重算任务状态不受支持",
        )
    query = (
        select(ReportRecomputeTask)
        .where(ReportRecomputeTask.requested_company_id == actor.company_id)
        .order_by(ReportRecomputeTask.created_at.desc(), ReportRecomputeTask.id.desc())
        .limit(limit)
    )
    if task_status:
        query = query.where(ReportRecomputeTask.status == task_status)
    tasks = db.scalars(query).all()
    return [_serialize_report_recompute_task(task) for task in tasks]


def retry_summary_report_recompute_task(
    db: Session,
    *,
    actor: AuthenticatedActor,
    task_id: int,
) -> ReportRecomputeTaskResult:
    task = _get_accessible_report_recompute_task(db, actor=actor, task_id=task_id)
    if task.status != RECOMPUTE_STATUS_FAILED:
        raise ReportServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前重算任务不支持重试",
        )
    request_fingerprint = _build_recompute_request_fingerprint(
        requested_by=task.requested_by,
        requested_company_id=task.requested_company_id,
        metric_version=task.metric_version,
        report_codes=_normalize_summary_report_codes(task.report_codes or []),
        reason=task.reason,
    )
    existing_task = _find_in_progress_report_recompute_task(
        db,
        request_fingerprint=request_fingerprint,
    )
    if existing_task is not None and existing_task.id != task.id:
        raise ReportServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="已存在相同范围的未完成重算任务，请直接查看当前任务结果",
        )
    before_payload = _report_recompute_task_audit_payload(task)
    task.idempotency_key = request_fingerprint
    task.status = RECOMPUTE_STATUS_PENDING
    task.error_message = None
    task.result_payload = {}
    task.finished_at = None
    task.retry_count += 1
    _append_report_recompute_audit_log(
        db,
        task=task,
        event_code=REPORT_RECOMPUTE_AUDIT_RETRIED,
        operator_id=actor.user_id,
        before_payload=before_payload,
    )
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        existing_task = _find_in_progress_report_recompute_task(
            db,
            request_fingerprint=request_fingerprint,
        )
        if existing_task is not None and existing_task.id != task.id:
            raise ReportServiceError(
                status_code=status.HTTP_409_CONFLICT,
                detail="已存在相同范围的未完成重算任务，请直接查看当前任务结果",
            ) from exc
        raise ReportServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重算任务重试失败，请稍后重试",
        ) from exc
    db.refresh(task)
    return _serialize_report_recompute_task(task)


def execute_summary_report_recompute_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(ReportRecomputeTask, task_id)
        if task is None:
            return
        before_payload = _report_recompute_task_audit_payload(task)
        task.status = RECOMPUTE_STATUS_PROCESSING
        task.error_message = None
        task.finished_at = None
        task.result_payload = {}
        _append_report_recompute_audit_log(
            db,
            task=task,
            event_code=REPORT_RECOMPUTE_AUDIT_PROCESSING,
            operator_id=task.requested_by,
            before_payload=before_payload,
        )
        _commit_or_raise(db, detail="重算任务状态更新失败，请稍后重试")
        db.refresh(task)

        _ensure_daily_contract_scan(db, trigger_source=RECOMPUTE_TRIGGER_SOURCE)
        result_payload: dict[str, dict[str, str]] = {}
        for report_code in _normalize_summary_report_codes(task.report_codes or []):
            snapshot = _force_create_summary_report_snapshot(
                db,
                report_code=report_code,
                metric_version=task.metric_version,
            )
            result_payload[report_code] = {
                "report_name": SUMMARY_REPORT_LABELS[report_code],
                "snapshot_time": snapshot.snapshot_time.isoformat(),
            }

        before_payload = _report_recompute_task_audit_payload(task)
        task.idempotency_key = _build_recompute_history_key(task, "completed")
        task.status = RECOMPUTE_STATUS_COMPLETED
        task.result_payload = result_payload
        task.error_message = None
        task.finished_at = datetime.now(UTC)
        _append_report_recompute_audit_log(
            db,
            task=task,
            event_code=REPORT_RECOMPUTE_AUDIT_COMPLETED,
            operator_id=task.requested_by,
            before_payload=before_payload,
        )
        _commit_or_raise(db, detail="重算任务结果保存失败，请稍后重试")
    except ReportServiceError as exc:
        _safely_mark_report_recompute_task_failed(task_id, exc.detail)
    except Exception:
        _safely_mark_report_recompute_task_failed(
            task_id,
            "重算任务执行失败，请稍后重试",
        )
    finally:
        db.close()


def _force_create_summary_report_snapshot(
    db: Session,
    *,
    report_code: str,
    metric_version: str,
) -> ReportSnapshot:
    version = _resolve_metric_version(metric_version)
    builder = _resolve_summary_report_builder(report_code)
    snapshot = ReportSnapshot(
        report_code=report_code,
        version=version,
        metric_payload=builder(db),
        snapshot_time=datetime.now(UTC),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _resolve_summary_report_builder(report_code: str):
    if report_code == REPORT_CODE_DASHBOARD:
        return _build_dashboard_payload
    if report_code == REPORT_CODE_BOARD:
        return _build_board_payload
    if report_code == REPORT_CODE_LIGHT:
        return _build_light_payload
    raise ReportServiceError(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="汇总报表编码不受支持",
    )


def _normalize_summary_report_codes(report_codes: list[str]) -> list[str]:
    normalized_codes = sorted(
        {str(code).strip() for code in report_codes if str(code).strip()}
    )
    if not normalized_codes:
        raise ReportServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="至少选择一个汇总报表",
        )
    unsupported_codes = [
        code for code in normalized_codes if code not in SUMMARY_REPORT_CODE_SCOPE
    ]
    if unsupported_codes:
        raise ReportServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="汇总报表编码不受支持",
        )
    return normalized_codes


def _normalize_recompute_reason(reason: str) -> str:
    normalized = str(reason or "").strip()
    if not normalized:
        raise ReportServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="重算原因不能为空",
        )
    return normalized[:255]


def _build_recompute_request_fingerprint(
    *,
    requested_by: str,
    requested_company_id: str | None,
    metric_version: str,
    report_codes: list[str],
    reason: str,
) -> str:
    fingerprint = hashlib.sha1(
        (
            f"summary-recompute|{metric_version}|{requested_by}|"
            f"{','.join(report_codes)}|{reason}|{requested_company_id or 'no-company'}"
        ).encode("utf-8")
    ).hexdigest()
    return f"summary-recompute:{fingerprint}"


def _build_recompute_idempotency_key(*, request_fingerprint: str) -> str:
    return f"{request_fingerprint}:{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"


def _build_recompute_history_key(task: ReportRecomputeTask, suffix: str) -> str:
    request_fingerprint = _build_recompute_request_fingerprint(
        requested_by=task.requested_by,
        requested_company_id=task.requested_company_id,
        metric_version=task.metric_version,
        report_codes=_normalize_summary_report_codes(task.report_codes or []),
        reason=task.reason,
    )
    return _build_recompute_idempotency_key(
        request_fingerprint=f"{request_fingerprint}:{suffix}:{task.id}"
    )


def _serialize_report_recompute_task(
    task: ReportRecomputeTask,
) -> ReportRecomputeTaskResult:
    return ReportRecomputeTaskResult(
        id=task.id,
        task_name=task.task_name,
        status=task.status,
        metric_version=task.metric_version,
        report_codes=[str(code) for code in task.report_codes or []],
        reason=task.reason,
        requested_by=task.requested_by,
        requested_role_code=task.requested_role_code,
        requested_company_id=task.requested_company_id,
        retry_count=task.retry_count,
        error_message=task.error_message,
        result_payload={
            str(key): {
                "report_name": str((value or {}).get("report_name") or ""),
                "snapshot_time": str((value or {}).get("snapshot_time") or ""),
            }
            for key, value in (task.result_payload or {}).items()
        },
        finished_at=task.finished_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _report_recompute_task_audit_payload(
    task: ReportRecomputeTask,
) -> dict[str, object]:
    return {
        "status": task.status,
        "metric_version": task.metric_version,
        "report_codes": task.report_codes,
        "reason": task.reason,
        "retry_count": task.retry_count,
        "error_message": task.error_message,
        "result_payload": task.result_payload,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
    }


def _append_report_recompute_audit_log(
    db: Session,
    *,
    task: ReportRecomputeTask,
    event_code: str,
    operator_id: str,
    before_payload: dict[str, object],
) -> None:
    db.add(
        BusinessAuditLog(
            event_code=event_code,
            biz_type=REPORT_RECOMPUTE_BIZ_TYPE,
            biz_id=str(task.id),
            operator_id=operator_id,
            before_json=before_payload,
            after_json=_report_recompute_task_audit_payload(task),
            extra_json={
                "task_name": task.task_name,
                "requested_company_id": task.requested_company_id,
            },
        )
    )


def _get_accessible_report_recompute_task(
    db: Session, *, actor: AuthenticatedActor, task_id: int
) -> ReportRecomputeTask:
    task = db.scalar(
        select(ReportRecomputeTask).where(
            ReportRecomputeTask.id == task_id,
            ReportRecomputeTask.requested_company_id == actor.company_id,
        )
    )
    if task is None:
        raise ReportServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="重算任务不存在或无权访问",
        )
    return task


def _find_in_progress_report_recompute_task(
    db: Session,
    *,
    request_fingerprint: str,
) -> ReportRecomputeTask | None:
    return db.scalar(
        select(ReportRecomputeTask)
        .where(
            ReportRecomputeTask.idempotency_key == request_fingerprint,
            ReportRecomputeTask.status.in_(
                [RECOMPUTE_STATUS_PENDING, RECOMPUTE_STATUS_PROCESSING]
            ),
        )
        .order_by(ReportRecomputeTask.created_at.desc(), ReportRecomputeTask.id.desc())
        .limit(1)
    )


def _mark_report_recompute_task_failed(
    db: Session,
    *,
    task: ReportRecomputeTask,
    detail: str,
    operator_id: str,
) -> None:
    before_payload = _report_recompute_task_audit_payload(task)
    task.idempotency_key = _build_recompute_history_key(task, "failed")
    task.status = RECOMPUTE_STATUS_FAILED
    task.error_message = _truncate_recompute_error(detail)
    task.finished_at = datetime.now(UTC)
    _append_report_recompute_audit_log(
        db,
        task=task,
        event_code=REPORT_RECOMPUTE_AUDIT_FAILED,
        operator_id=operator_id,
        before_payload=before_payload,
    )
    _commit_or_raise(db, detail="重算任务失败状态保存失败，请稍后重试")


def _safely_mark_report_recompute_task_failed(task_id: int, detail: str) -> None:
    db = SessionLocal()
    try:
        task = db.get(ReportRecomputeTask, task_id)
        if task is None:
            return
        _mark_report_recompute_task_failed(
            db,
            task=task,
            detail=detail,
            operator_id=task.requested_by,
        )
    except Exception:
        db.rollback()
    finally:
        db.close()


def _truncate_recompute_error(detail: str) -> str:
    normalized = str(detail or "").strip() or "重算任务执行失败，请稍后重试"
    return normalized[:255]


def _commit_or_raise(db: Session, *, detail: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise ReportServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from exc


__all__ = [
    "METRIC_VERSION_V1",
    "RECOMPUTE_STATUS_COMPLETED",
    "RECOMPUTE_STATUS_FAILED",
    "RECOMPUTE_STATUS_PENDING",
    "RECOMPUTE_STATUS_PROCESSING",
    "SUMMARY_REPORT_CODE_SCOPE",
    "create_summary_report_recompute_task",
    "execute_summary_report_recompute_task",
    "list_summary_report_recompute_tasks",
    "retry_summary_report_recompute_task",
]
