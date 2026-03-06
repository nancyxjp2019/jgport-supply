from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, get_current_actor
from app.db.session import get_db
from app.models.business_audit_log import BusinessAuditLog
from app.models.role_company_binding import RoleCompanyBinding
from app.schemas.access import AccessCheckRequest, AccessCheckResponse, AccessMeResponse

router = APIRouter(prefix="/access", tags=["access"])


@router.get("/me", response_model=AccessMeResponse)
def get_access_me(
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> AccessMeResponse:
    binding = _get_active_binding(db, actor)
    return AccessMeResponse(
        user_id=actor.user_id,
        role_code=actor.role_code,
        company_id=actor.company_id,
        company_type=actor.company_type,
        client_type=actor.client_type,
        admin_web_allowed=bool(binding.admin_web_allowed) if binding else False,
        miniprogram_allowed=bool(binding.miniprogram_allowed) if binding else False,
        message="身份读取成功",
    )


@router.post("/check", response_model=AccessCheckResponse)
def check_access(
    payload: AccessCheckRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> AccessCheckResponse:
    binding = _get_active_binding(db, actor)
    if binding is None:
        message = "角色与公司归属不匹配，禁止登录"
        _write_access_audit(db, actor, payload.target_client_type, allowed=False, message=message)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    allowed = (
        binding.admin_web_allowed
        if payload.target_client_type == "admin_web"
        else binding.miniprogram_allowed
    )
    if not allowed:
        message = "当前角色不允许登录该端"
        _write_access_audit(db, actor, payload.target_client_type, allowed=False, message=message)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    message = "访问校验通过"
    _write_access_audit(db, actor, payload.target_client_type, allowed=True, message=message)
    return AccessCheckResponse(allowed=True, message=message)


def _get_active_binding(db: Session, actor: AuthenticatedActor) -> RoleCompanyBinding | None:
    statement = (
        select(RoleCompanyBinding)
        .where(
            RoleCompanyBinding.role_code == actor.role_code,
            RoleCompanyBinding.company_type == actor.company_type,
            RoleCompanyBinding.is_active.is_(True),
            RoleCompanyBinding.status == "生效",
        )
        .order_by(RoleCompanyBinding.version.desc())
        .limit(1)
    )
    return db.scalar(statement)


def _write_access_audit(
    db: Session,
    actor: AuthenticatedActor,
    target_client_type: str,
    *,
    allowed: bool,
    message: str,
) -> None:
    log = BusinessAuditLog(
        event_code="M1-ACCESS-CHECK",
        biz_type="access_policy",
        biz_id=f"{actor.role_code}:{actor.company_type}:{target_client_type}",
        operator_id=actor.user_id,
        before_json={},
        after_json={"allowed": allowed, "target_client_type": target_client_type},
        extra_json={"message": message},
    )
    db.add(log)
    db.commit()
