from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.business_audit_log import BusinessAuditLog
from app.models.role_company_binding import RoleCompanyBinding
from app.schemas.access import AccessCheckRequest, AccessCheckResponse

router = APIRouter(prefix="/access", tags=["access"])


@router.post("/check", response_model=AccessCheckResponse)
def check_access(payload: AccessCheckRequest, db: Session = Depends(get_db)) -> AccessCheckResponse:
    statement = (
        select(RoleCompanyBinding)
        .where(
            RoleCompanyBinding.role_code == payload.role_code,
            RoleCompanyBinding.company_type == payload.company_type,
            RoleCompanyBinding.status == "生效",
        )
        .order_by(RoleCompanyBinding.version.desc())
        .limit(1)
    )
    binding = db.scalar(statement)
    if binding is None:
        message = "角色与公司归属不匹配，禁止登录"
        _write_access_audit(db, payload, allowed=False, message=message)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    allowed = binding.admin_web_allowed if payload.client_type == "admin_web" else binding.miniprogram_allowed
    if not allowed:
        message = "当前角色不允许登录该端"
        _write_access_audit(db, payload, allowed=False, message=message)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    message = "访问校验通过"
    _write_access_audit(db, payload, allowed=True, message=message)
    return AccessCheckResponse(allowed=True, message=message)


def _write_access_audit(
    db: Session,
    payload: AccessCheckRequest,
    *,
    allowed: bool,
    message: str,
) -> None:
    log = BusinessAuditLog(
        event_code="M1-ACCESS-CHECK",
        biz_type="access_policy",
        biz_id=f"{payload.role_code}:{payload.company_type}:{payload.client_type}",
        operator_id=payload.role_code,
        before_json={},
        after_json={"allowed": allowed},
        extra_json={"message": message},
    )
    db.add(log)
    db.commit()
