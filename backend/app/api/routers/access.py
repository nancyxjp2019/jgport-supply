from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, get_current_actor
from app.core.direct_auth_token import (
    TOKEN_EXPIRES_IN_SECONDS,
    issue_direct_auth_token,
    verify_direct_auth_token_for_refresh,
)
from app.db.session import get_db
from app.models.business_audit_log import BusinessAuditLog
from app.models.role_company_binding import RoleCompanyBinding
from app.schemas.access import (
    AccessCheckRequest,
    AccessCheckResponse,
    AccessMeResponse,
    AccessSessionRefreshResponse,
)

router = APIRouter(prefix="/access", tags=["access"])


@router.get("/me", response_model=AccessMeResponse)
def get_access_me(
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> AccessMeResponse:
    binding = _get_active_binding(db, actor)
    return AccessMeResponse(
        **_build_access_profile_payload(actor, binding),
        message="身份读取成功",
    )


@router.post("/session/refresh", response_model=AccessSessionRefreshResponse)
def refresh_access_session(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> AccessSessionRefreshResponse:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话续期仅支持登录令牌",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录令牌格式不正确",
        )
    actor = verify_direct_auth_token_for_refresh(token.strip())
    binding = _get_active_binding(db, actor)
    if binding is None:
        message = "角色与公司归属不匹配，禁止续期"
        _write_access_audit(
            db,
            actor,
            actor.client_type,
            allowed=False,
            message=message,
            event_code="M8-ACCESS-SESSION-REFRESH",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
    if not _resolve_client_access(binding, actor.client_type):
        message = "当前角色不允许在该端续期会话"
        _write_access_audit(
            db,
            actor,
            actor.client_type,
            allowed=False,
            message=message,
            event_code="M8-ACCESS-SESSION-REFRESH",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    access_token = issue_direct_auth_token(actor)
    _write_access_audit(
        db,
        actor,
        actor.client_type,
        allowed=True,
        message="会话续期成功",
        event_code="M8-ACCESS-SESSION-REFRESH",
    )
    return AccessSessionRefreshResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in_seconds=TOKEN_EXPIRES_IN_SECONDS,
        **_build_access_profile_payload(actor, binding),
        message="会话续期成功",
    )


def _build_access_profile_payload(
    actor: AuthenticatedActor,
    binding: RoleCompanyBinding | None,
) -> dict[str, object]:
    return {
        "user_id": actor.user_id,
        "role_code": actor.role_code,
        "company_id": actor.company_id,
        "company_type": actor.company_type,
        "client_type": actor.client_type,
        "admin_web_allowed": bool(binding.admin_web_allowed) if binding else False,
        "miniprogram_allowed": bool(binding.miniprogram_allowed) if binding else False,
    }


@router.post("/check", response_model=AccessCheckResponse)
def check_access(
    payload: AccessCheckRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> AccessCheckResponse:
    binding = _get_active_binding(db, actor)
    if binding is None:
        message = "角色与公司归属不匹配，禁止登录"
        _write_access_audit(
            db, actor, payload.target_client_type, allowed=False, message=message
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    allowed = _resolve_client_access(binding, payload.target_client_type)
    if not allowed:
        message = "当前角色不允许登录该端"
        _write_access_audit(
            db, actor, payload.target_client_type, allowed=False, message=message
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

    message = "访问校验通过"
    _write_access_audit(
        db, actor, payload.target_client_type, allowed=True, message=message
    )
    return AccessCheckResponse(allowed=True, message=message)


def _get_active_binding(
    db: Session, actor: AuthenticatedActor
) -> RoleCompanyBinding | None:
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
    event_code: str = "M1-ACCESS-CHECK",
) -> None:
    log = BusinessAuditLog(
        event_code=event_code,
        biz_type="access_policy",
        biz_id=f"{actor.role_code}:{actor.company_type}:{target_client_type}",
        operator_id=actor.user_id,
        before_json={},
        after_json={"allowed": allowed, "target_client_type": target_client_type},
        extra_json={"message": message},
    )
    db.add(log)
    db.commit()


def _resolve_client_access(
    binding: RoleCompanyBinding, target_client_type: str
) -> bool:
    if target_client_type not in {"admin_web", "miniprogram"}:
        return False
    return (
        bool(binding.admin_web_allowed)
        if target_client_type == "admin_web"
        else bool(binding.miniprogram_allowed)
    )
