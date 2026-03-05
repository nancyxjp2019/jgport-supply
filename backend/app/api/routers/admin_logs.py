from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AdminOperator, get_admin_operator
from app.db.session import get_db
from app.models.business_log import BusinessLog
from app.schemas.business_log import BusinessLogOut
from app.services.business_log_service import write_business_log

router = APIRouter(prefix="/admin", tags=["admin-logs"])


@router.get("/business-logs", response_model=list[BusinessLogOut])
def list_business_logs(
    request: Request,
    action: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    result: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> list[BusinessLogOut]:
    query = select(BusinessLog)
    if action:
        query = query.where(BusinessLog.action == action)
    if user_id is not None:
        query = query.where(BusinessLog.user_id == user_id)
    if result:
        query = query.where(BusinessLog.result == result)

    logs = db.scalars(
        query.order_by(BusinessLog.id.desc()).offset(offset).limit(limit)
    ).all()

    write_business_log(
        db=db,
        request=request,
        action="ADMIN_BUSINESS_LOG_LIST",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="BUSINESS_LOG",
        detail_json={
            "count": len(logs),
            "limit": limit,
            "offset": offset,
            "action_filter": action,
            "user_filter": user_id,
            "result_filter": result,
        },
        auto_commit=True,
    )
    return [BusinessLogOut.model_validate(item) for item in logs]
