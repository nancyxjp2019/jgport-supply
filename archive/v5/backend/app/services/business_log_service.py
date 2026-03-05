from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.logging_config import get_business_logger, get_system_logger
from app.models.business_log import BusinessLog
from app.models.user import User


def write_business_log(
    db: Session,
    request: Request,
    action: str,
    result: str,
    user: User | None = None,
    actor_user_id: int | None = None,
    role: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    order_id: int | None = None,
    before_status: str | None = None,
    after_status: str | None = None,
    reason: str | None = None,
    detail_json: dict[str, Any] | None = None,
    auto_commit: bool = False,
) -> BusinessLog:
    request_id = getattr(request.state, "request_id", None)
    ip = request.client.host if request.client else None

    record = BusinessLog(
        request_id=request_id,
        user_id=actor_user_id if actor_user_id is not None else (user.id if user else None),
        role=role or (user.role.value if user else None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        order_id=order_id,
        before_status=before_status,
        after_status=after_status,
        result=result,
        reason=reason,
        ip=ip,
        detail_json=detail_json or {},
    )
    db.add(record)
    if auto_commit:
        try:
            db.commit()
            db.refresh(record)
        except Exception:
            db.rollback()
            get_system_logger().exception(
                "业务日志写入失败",
                extra={
                    "action": action,
                    "result": result,
                    "request_id": request_id,
                },
            )
            raise

    get_business_logger().info(
        "业务日志写入",
        extra={
            "action": action,
            "result": result,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "order_id": order_id,
            "reason": reason,
        },
    )
    return record
