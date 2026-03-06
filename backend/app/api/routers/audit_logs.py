from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.business_audit_log import BusinessAuditLog
from app.schemas.audit import AuditLogCreateRequest, AuditLogItem, AuditLogListResponse
from app.services.audit_log_service import AuditWriteFailedError, write_audit_log_with_retry

router = APIRouter(prefix="/audit/logs", tags=["audit"])


@router.post("")
def create_audit_log(payload: AuditLogCreateRequest) -> dict[str, str | int]:
    try:
        log = write_audit_log_with_retry(
            SessionLocal,
            payload=payload.model_dump(),
            max_retries=3,
        )
    except AuditWriteFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="审计日志写入失败，请联系管理员",
        ) from exc
    return {"id": log.id, "message": "审计日志写入成功"}


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    biz_id: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    statement = select(BusinessAuditLog).order_by(BusinessAuditLog.id.desc()).limit(limit)
    if biz_id:
        statement = statement.where(BusinessAuditLog.biz_id == biz_id)
    rows = db.scalars(statement).all()
    return AuditLogListResponse(
        items=[
            AuditLogItem(
                id=row.id,
                event_code=row.event_code,
                biz_type=row.biz_type,
                biz_id=row.biz_id,
                operator_id=row.operator_id,
                before_json=row.before_json,
                after_json=row.after_json,
                extra_json=row.extra_json,
                occurred_at=row.occurred_at,
            )
            for row in rows
        ]
    )
