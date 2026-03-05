from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.activation_code import ActivationCode
from app.models.user import User, UserStatus
from app.models.wechat_account import WeChatAccount
from app.schemas.auth import WeChatBindRequest, WeChatLoginRequest, WeChatLoginResponse
from app.schemas.user import UserOut
from app.services.business_log_service import write_business_log
from app.services.wechat_auth_service import (
    WeChatResolveOpenIdError,
    cache_openid_by_login_code,
    pop_cached_openid_by_login_code,
    resolve_openid_from_login_code,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _resolve_activation_for_bind(db: Session, activation_code: str) -> ActivationCode | None:
    return db.scalar(select(ActivationCode).where(ActivationCode.code == activation_code))


def _resolve_openid_or_raise(
    *,
    payload_code: str,
    db: Session,
    request: Request,
    action: str,
) -> str:
    try:
        return resolve_openid_from_login_code(payload_code)
    except WeChatResolveOpenIdError as exc:
        write_business_log(
            db=db,
            request=request,
            action=action,
            result="FAILED",
            reason=exc.reason,
            detail_json=exc.detail_json,
            auto_commit=True,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail_code) from exc


@router.post("/wechat/login", response_model=WeChatLoginResponse)
def wechat_login(
    payload: WeChatLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WeChatLoginResponse:
    openid = _resolve_openid_or_raise(
        payload_code=payload.code,
        db=db,
        request=request,
        action="AUTH_WECHAT_LOGIN",
    )
    account = db.scalar(select(WeChatAccount).where(WeChatAccount.openid == openid))
    if account is None:
        cache_openid_by_login_code(code=payload.code, openid=openid)
        write_business_log(
            db=db,
            request=request,
            action="AUTH_WECHAT_LOGIN",
            result="NEED_ACTIVATION",
            reason="微信账号未绑定",
            detail_json={"openid_hint": f"{openid[:18]}..."},
            auto_commit=True,
        )
        return WeChatLoginResponse(
            activation_required=True,
            openid_hint=f"{openid[:18]}...",
        )

    user = db.scalar(select(User).where(User.id == account.user_id))
    if user is None:
        write_business_log(
            db=db,
            request=request,
            action="AUTH_WECHAT_LOGIN",
            result="FAILED",
            reason="绑定账号不存在",
            detail_json={"openid_hint": f"{openid[:18]}..."},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    if user.status != UserStatus.ACTIVE:
        write_business_log(
            db=db,
            request=request,
            action="AUTH_WECHAT_LOGIN",
            result="FAILED",
            user=user,
            entity_type="USER",
            entity_id=str(user.id),
            reason="用户未激活或已禁用",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user_not_active")

    token, expires_in = create_access_token(subject=str(user.id), role=user.role.value)
    write_business_log(
        db=db,
        request=request,
        action="AUTH_WECHAT_LOGIN",
        result="SUCCESS",
        user=user,
        entity_type="USER",
        entity_id=str(user.id),
        auto_commit=True,
    )
    return WeChatLoginResponse(
        activation_required=False,
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


@router.post("/wechat/bind", response_model=WeChatLoginResponse)
def wechat_bind(
    payload: WeChatBindRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> WeChatLoginResponse:
    now = datetime.now(UTC)
    activation = _resolve_activation_for_bind(db=db, activation_code=payload.activation_code)
    if activation is None:
        write_business_log(
            db=db,
            request=request,
            action="AUTH_WECHAT_BIND",
            result="FAILED",
            reason="激活码不存在",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="activation_code_invalid")
    if activation.used_at is not None:
        write_business_log(
            db=db,
            request=request,
            action="AUTH_WECHAT_BIND",
            result="FAILED",
            entity_type="USER",
            entity_id=str(activation.user_id),
            reason="激活码已使用",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="activation_code_used")
    expires_at = activation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < now:
        write_business_log(
            db=db,
            request=request,
            action="AUTH_WECHAT_BIND",
            result="FAILED",
            entity_type="USER",
            entity_id=str(activation.user_id),
            reason="激活码已过期",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="activation_code_expired")

    openid = pop_cached_openid_by_login_code(payload.code)
    if openid is None:
        openid = _resolve_openid_or_raise(
            payload_code=payload.code,
            db=db,
            request=request,
            action="AUTH_WECHAT_BIND",
        )
    existing_openid_account = db.scalar(select(WeChatAccount).where(WeChatAccount.openid == openid))
    if existing_openid_account and existing_openid_account.user_id != activation.user_id:
        write_business_log(
            db=db,
            request=request,
            action="AUTH_WECHAT_BIND",
            result="FAILED",
            entity_type="USER",
            entity_id=str(activation.user_id),
            reason="微信账号已绑定其他用户",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="openid_already_bound")

    account = db.scalar(select(WeChatAccount).where(WeChatAccount.user_id == activation.user_id))
    if account is None:
        account = WeChatAccount(user_id=activation.user_id, openid=openid)
        db.add(account)
    else:
        account.openid = openid

    user = db.scalar(select(User).where(User.id == activation.user_id))
    if user is None:
        write_business_log(
            db=db,
            request=request,
            action="AUTH_WECHAT_BIND",
            result="FAILED",
            entity_type="USER",
            entity_id=str(activation.user_id),
            reason="激活用户不存在",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    before_status = user.status.value
    activation.used_at = now
    if user.status == UserStatus.PENDING_ACTIVATION:
        user.status = UserStatus.ACTIVE

    write_business_log(
        db=db,
        request=request,
        action="AUTH_WECHAT_BIND",
        result="SUCCESS",
        user=user,
        entity_type="USER",
        entity_id=str(user.id),
        before_status=before_status,
        after_status=user.status.value,
    )
    db.commit()
    db.refresh(user)

    token, expires_in = create_access_token(subject=str(user.id), role=user.role.value)
    return WeChatLoginResponse(
        activation_required=False,
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    write_business_log(
        db=db,
        request=request,
        action="AUTH_ME",
        result="SUCCESS",
        user=current_user,
        entity_type="USER",
        entity_id=str(current_user.id),
        auto_commit=True,
    )
    return UserOut.model_validate(current_user)
