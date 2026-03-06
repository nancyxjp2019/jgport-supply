from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.direct_auth_token import TOKEN_EXPIRES_IN_SECONDS, issue_direct_auth_token
from app.core.auth_actor import AuthenticatedActor
from app.db.session import get_db
from app.models.business_audit_log import BusinessAuditLog
from app.models.role_company_binding import RoleCompanyBinding
from app.schemas.mini_auth import MiniProgramDevLoginRequest, MiniProgramDevLoginResponse

router = APIRouter(prefix="/mini-auth", tags=["mini-auth"])

DEV_MINIPROGRAM_ACTORS = {
    "operations": {
        "user_id": "AUTO-TEST-MINI-OPS-001",
        "company_id": "AUTO-TEST-OPERATOR-COMPANY",
        "company_type": "operator_company",
    },
    "finance": {
        "user_id": "AUTO-TEST-MINI-FIN-001",
        "company_id": "AUTO-TEST-OPERATOR-COMPANY",
        "company_type": "operator_company",
    },
    "admin": {
        "user_id": "AUTO-TEST-MINI-ADMIN-001",
        "company_id": "AUTO-TEST-OPERATOR-COMPANY",
        "company_type": "operator_company",
    },
    "customer": {
        "user_id": "AUTO-TEST-MINI-CUSTOMER-001",
        "company_id": "AUTO-TEST-CUSTOMER-COMPANY",
        "company_type": "customer_company",
    },
    "supplier": {
        "user_id": "AUTO-TEST-MINI-SUPPLIER-001",
        "company_id": "AUTO-TEST-SUPPLIER-COMPANY",
        "company_type": "supplier_company",
    },
    "warehouse": {
        "user_id": "AUTO-TEST-MINI-WAREHOUSE-001",
        "company_id": "AUTO-TEST-WAREHOUSE-COMPANY",
        "company_type": "warehouse_company",
    },
}


@router.post("/dev-login", response_model=MiniProgramDevLoginResponse)
def miniprogram_dev_login(
    payload: MiniProgramDevLoginRequest,
    db: Session = Depends(get_db),
) -> MiniProgramDevLoginResponse:
    settings = get_settings()
    if str(settings.env or "").strip().lower() not in {"dev", "test"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前环境未开放小程序本地联调登录")

    actor_template = DEV_MINIPROGRAM_ACTORS[payload.role_code]
    actor = AuthenticatedActor(
        user_id=actor_template["user_id"],
        role_code=payload.role_code,
        company_id=actor_template["company_id"],
        company_type=actor_template["company_type"],
        client_type="miniprogram",
    )
    binding = _get_active_binding(db, actor)
    if binding is None or not bool(binding.miniprogram_allowed):
        _write_login_audit(db, actor, allowed=False, message="当前角色不允许本地登录小程序")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色不允许本地登录小程序")

    access_token = issue_direct_auth_token(actor)
    _write_login_audit(db, actor, allowed=True, message="小程序本地联调登录成功")
    return MiniProgramDevLoginResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in_seconds=TOKEN_EXPIRES_IN_SECONDS,
        user_id=actor.user_id,
        role_code=actor.role_code,
        company_id=actor.company_id,
        company_type=actor.company_type,
        client_type=actor.client_type,
        admin_web_allowed=bool(binding.admin_web_allowed),
        miniprogram_allowed=bool(binding.miniprogram_allowed),
        message="小程序本地联调登录成功",
    )


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


def _write_login_audit(db: Session, actor: AuthenticatedActor, *, allowed: bool, message: str) -> None:
    db.add(
        BusinessAuditLog(
            event_code="M8-MINI-DEV-LOGIN",
            biz_type="mini_dev_login",
            biz_id=f"{actor.role_code}:{actor.company_type}",
            operator_id=actor.user_id,
            before_json={},
            after_json={"allowed": allowed, "client_type": actor.client_type},
            extra_json={"message": message},
        )
    )
    db.commit()
