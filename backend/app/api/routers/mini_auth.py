from __future__ import annotations

from datetime import UTC, datetime
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.direct_auth_token import TOKEN_EXPIRES_IN_SECONDS, issue_direct_auth_token
from app.core.auth_actor import AuthenticatedActor
from app.db.session import get_db
from app.models.business_audit_log import BusinessAuditLog
from app.models.mini_program_account import MiniProgramAccount
from app.models.role_company_binding import RoleCompanyBinding
from app.schemas.mini_auth import MiniProgramDevLoginRequest, MiniProgramDevLoginResponse
from app.schemas.wechat_auth import MiniProgramWeChatLoginRequest, MiniProgramWeChatLoginResponse
import app.services.wechat_login_service as wechat_login_service

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


@router.post("/wechat-login", response_model=MiniProgramWeChatLoginResponse)
def miniprogram_wechat_login(
    payload: MiniProgramWeChatLoginRequest,
    db: Session = Depends(get_db),
) -> MiniProgramWeChatLoginResponse:
    try:
        session_result = wechat_login_service.exchange_wechat_code2session(payload.code)
    except wechat_login_service.WeChatLoginServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    account = db.scalar(
        select(MiniProgramAccount).where(
            MiniProgramAccount.openid == session_result.openid,
            MiniProgramAccount.status == "生效",
            MiniProgramAccount.is_active.is_(True),
        )
    )
    if account is None:
        _write_wechat_login_audit(
            db,
            openid=session_result.openid,
            allowed=False,
            message="当前微信账号未绑定业务角色",
        )
        settings = get_settings()
        normalized_env = str(settings.env or "").strip().lower()
        return MiniProgramWeChatLoginResponse(
            binding_required=True,
            openid_hint=_mask_openid(session_result.openid),
            debug_openid=session_result.openid if normalized_env in {"dev", "test"} else None,
            message="当前微信账号未绑定业务角色，请联系管理员",
        )

    actor = AuthenticatedActor(
        user_id=f"MINI-WX-{account.id}",
        role_code=account.role_code,
        company_id=account.company_id,
        company_type=account.company_type,
        client_type="miniprogram",
    )
    binding = _get_active_binding(db, actor)
    if binding is None or not bool(binding.miniprogram_allowed):
        _write_wechat_login_audit(
            db,
            openid=session_result.openid,
            allowed=False,
            message="当前微信账号绑定的角色未开放小程序访问",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前微信账号未开放小程序访问")

    account.unionid = session_result.unionid
    account.last_login_at = datetime.now(UTC)
    db.add(account)
    access_token = issue_direct_auth_token(actor)
    db.add(
        BusinessAuditLog(
            event_code="M8-MINI-WECHAT-LOGIN",
            biz_type="mini_wechat_login",
            biz_id=str(account.id),
            operator_id=actor.user_id,
            before_json={},
            after_json={"allowed": True, "role_code": actor.role_code, "company_type": actor.company_type},
            extra_json={"openid_hint": _mask_openid(session_result.openid), "message": "微信登录成功"},
        )
    )
    db.commit()

    return MiniProgramWeChatLoginResponse(
        binding_required=False,
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
        openid_hint=_mask_openid(session_result.openid),
        message="微信登录成功",
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


def _write_wechat_login_audit(db: Session, *, openid: str, allowed: bool, message: str) -> None:
    db.add(
        BusinessAuditLog(
            event_code="M8-MINI-WECHAT-LOGIN",
            biz_type="mini_wechat_login",
            biz_id=_hash_openid(openid),
            operator_id="MINI-WECHAT-LOGIN",
            before_json={},
            after_json={"allowed": allowed},
            extra_json={"openid_hint": _mask_openid(openid), "message": message},
        )
    )
    db.commit()


def _mask_openid(openid: str) -> str:
    normalized = str(openid or "").strip()
    if len(normalized) <= 10:
        return normalized
    return f"{normalized[:6]}...{normalized[-4:]}"


def _hash_openid(openid: str) -> str:
    return hashlib.sha256(str(openid or "").encode("utf-8")).hexdigest()[:24]
