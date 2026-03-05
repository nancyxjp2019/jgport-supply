from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_super_admin
from app.core.rate_limit import InMemorySlidingWindowRateLimiter
from app.core.security import (
    create_super_admin_access_token,
    create_super_admin_challenge_token,
    decode_super_admin_challenge_token,
    hash_recovery_code,
    verify_password,
    verify_totp_code,
)
from app.core.test_env_shortcuts import is_test_env
from app.db.session import get_db
from app.models.super_admin import SuperAdminCredential, SuperAdminRecoveryCode
from app.schemas.admin_auth import (
    SuperAdminAuthResponse,
    SuperAdminLoginRequest,
    SuperAdminLoginResponse,
    SuperAdminLogoutResponse,
    SuperAdminOut,
    SuperAdminRecoveryVerifyRequest,
    SuperAdminTotpVerifyRequest,
)
from app.services.business_log_service import write_business_log

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

MAX_PASSWORD_RETRY = 5
LOCK_MINUTES = 15
MFA_VERIFY_RATE_LIMIT_COUNT = 10
MFA_VERIFY_RATE_LIMIT_WINDOW_SECONDS = 300

_mfa_verify_rate_limiter = InMemorySlidingWindowRateLimiter(
    max_requests=MFA_VERIFY_RATE_LIMIT_COUNT,
    window_seconds=MFA_VERIFY_RATE_LIMIT_WINDOW_SECONDS,
)


def _build_super_admin_out(admin: SuperAdminCredential) -> SuperAdminOut:
    return SuperAdminOut(
        id=admin.id,
        username=admin.username,
        display_name=admin.display_name,
        is_active=admin.is_active,
        created_at=admin.created_at,
        last_login_at=admin.last_login_at,
    )


def _build_super_admin_auth_response(admin: SuperAdminCredential) -> SuperAdminAuthResponse:
    access_token, expires_in = create_super_admin_access_token(subject=str(admin.id))
    return SuperAdminAuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        super_admin=_build_super_admin_out(admin),
    )


def _build_super_admin_login_response(
    *,
    admin: SuperAdminCredential,
    mfa_required: bool,
    challenge_token: str | None,
    challenge_expires_in: int | None,
) -> SuperAdminLoginResponse:
    if mfa_required:
        return SuperAdminLoginResponse(
            mfa_required=True,
            challenge_token=challenge_token,
            challenge_expires_in=challenge_expires_in,
        )

    auth_response = _build_super_admin_auth_response(admin)
    return SuperAdminLoginResponse(
        mfa_required=False,
        challenge_token=challenge_token,
        challenge_expires_in=challenge_expires_in,
        access_token=auth_response.access_token,
        token_type=auth_response.token_type,
        expires_in=auth_response.expires_in,
        super_admin=auth_response.super_admin,
    )


def _normalize_locked_until(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _extract_client_ip(request: Request) -> str:
    real_ip = (request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip
    forwarded = (request.headers.get("x-forwarded-for") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_mfa_verify_rate_limit(request: Request, admin_id: int, action: str, db: Session) -> None:
    client_ip = _extract_client_ip(request)
    limiter_key = f"{action}:{admin_id}:{client_ip}"
    rate_limit_result = _mfa_verify_rate_limiter.hit(limiter_key)
    if rate_limit_result.allowed:
        return
    write_business_log(
        db=db,
        request=request,
        action=action,
        result="FAILED",
        role="SUPER_ADMIN",
        entity_type="SUPER_ADMIN",
        entity_id=str(admin_id),
        reason="二次验证请求过于频繁",
        detail_json={
            "client_ip": client_ip,
            "retry_after_seconds": rate_limit_result.retry_after_seconds,
        },
        auto_commit=True,
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="too_many_requests",
        headers={"Retry-After": str(rate_limit_result.retry_after_seconds)},
    )


@router.post("/login", response_model=SuperAdminLoginResponse)
def super_admin_login(
    payload: SuperAdminLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> SuperAdminLoginResponse:
    username = payload.username.strip()
    admin = db.scalar(select(SuperAdminCredential).where(SuperAdminCredential.username == username))
    now = datetime.now(UTC)

    if admin is None:
        write_business_log(
            db=db,
            request=request,
            action="SUPER_ADMIN_LOGIN_PASSWORD",
            result="FAILED",
            role="SUPER_ADMIN",
            reason="账号不存在",
            detail_json={"username": username},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="username_or_password_invalid")

    locked_until = _normalize_locked_until(admin.locked_until)
    if locked_until is not None and locked_until > now:
        write_business_log(
            db=db,
            request=request,
            action="SUPER_ADMIN_LOGIN_PASSWORD",
            result="FAILED",
            role="SUPER_ADMIN",
            entity_type="SUPER_ADMIN",
            entity_id=str(admin.id),
            reason="账号已锁定",
            detail_json={"locked_until": locked_until.isoformat()},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="super_admin_locked")

    if not admin.is_active:
        write_business_log(
            db=db,
            request=request,
            action="SUPER_ADMIN_LOGIN_PASSWORD",
            result="FAILED",
            role="SUPER_ADMIN",
            entity_type="SUPER_ADMIN",
            entity_id=str(admin.id),
            reason="账号已停用",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super_admin_not_active")

    if not verify_password(payload.password, admin.password_hash):
        admin.failed_login_count += 1
        if admin.failed_login_count >= MAX_PASSWORD_RETRY:
            admin.failed_login_count = 0
            admin.locked_until = now + timedelta(minutes=LOCK_MINUTES)
        db.commit()
        write_business_log(
            db=db,
            request=request,
            action="SUPER_ADMIN_LOGIN_PASSWORD",
            result="FAILED",
            role="SUPER_ADMIN",
            entity_type="SUPER_ADMIN",
            entity_id=str(admin.id),
            reason="密码错误",
            detail_json={"failed_login_count": admin.failed_login_count},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="username_or_password_invalid")

    admin.failed_login_count = 0
    admin.locked_until = None
    challenge_token, challenge_expires_in = create_super_admin_challenge_token(admin_id=admin.id)

    if is_test_env():
        admin.last_login_at = now
        db.commit()
        db.refresh(admin)
        write_business_log(
            db=db,
            request=request,
            action="SUPER_ADMIN_LOGIN_PASSWORD",
            result="SUCCESS",
            role="SUPER_ADMIN",
            entity_type="SUPER_ADMIN",
            entity_id=str(admin.id),
            detail_json={
                "challenge_expires_in": challenge_expires_in,
                "mfa_required": False,
                "test_env_totp_bypassed": True,
            },
            auto_commit=True,
        )
        return _build_super_admin_login_response(
            admin=admin,
            mfa_required=False,
            challenge_token=challenge_token,
            challenge_expires_in=challenge_expires_in,
        )

    if admin.mfa is None or not admin.mfa.is_enabled:
        write_business_log(
            db=db,
            request=request,
            action="SUPER_ADMIN_LOGIN_PASSWORD",
            result="FAILED",
            role="SUPER_ADMIN",
            entity_type="SUPER_ADMIN",
            entity_id=str(admin.id),
            reason="MFA 未配置",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="super_admin_mfa_not_configured")

    db.commit()
    write_business_log(
        db=db,
        request=request,
        action="SUPER_ADMIN_LOGIN_PASSWORD",
        result="SUCCESS",
        role="SUPER_ADMIN",
        entity_type="SUPER_ADMIN",
        entity_id=str(admin.id),
        detail_json={"challenge_expires_in": challenge_expires_in, "mfa_required": True},
        auto_commit=True,
    )
    return _build_super_admin_login_response(
        admin=admin,
        mfa_required=True,
        challenge_token=challenge_token,
        challenge_expires_in=challenge_expires_in,
    )


@router.post("/totp/verify", response_model=SuperAdminAuthResponse)
def super_admin_totp_verify(
    payload: SuperAdminTotpVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> SuperAdminAuthResponse:
    try:
        challenge = decode_super_admin_challenge_token(payload.challenge_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_challenge_token") from exc

    subject = challenge.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_challenge_token")
    try:
        admin_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_challenge_token") from exc

    admin = db.scalar(select(SuperAdminCredential).where(SuperAdminCredential.id == admin_id))
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="super_admin_not_found")
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super_admin_not_active")
    if admin.mfa is None or not admin.mfa.is_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="super_admin_mfa_not_configured")
    _enforce_mfa_verify_rate_limit(
        request=request,
        admin_id=admin.id,
        action="SUPER_ADMIN_LOGIN_TOTP_VERIFY",
        db=db,
    )

    if not verify_totp_code(admin.mfa.totp_secret, payload.totp_code):
        write_business_log(
            db=db,
            request=request,
            action="SUPER_ADMIN_LOGIN_TOTP_VERIFY",
            result="FAILED",
            role="SUPER_ADMIN",
            entity_type="SUPER_ADMIN",
            entity_id=str(admin.id),
            reason="TOTP 验证码错误",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="totp_code_invalid")

    now = datetime.now(UTC)
    admin.last_login_at = now
    admin.mfa.last_verified_at = now
    db.commit()
    db.refresh(admin)

    write_business_log(
        db=db,
        request=request,
        action="SUPER_ADMIN_LOGIN_TOTP_VERIFY",
        result="SUCCESS",
        role="SUPER_ADMIN",
        entity_type="SUPER_ADMIN",
        entity_id=str(admin.id),
        auto_commit=True,
    )
    return _build_super_admin_auth_response(admin)


@router.post("/recovery/verify", response_model=SuperAdminAuthResponse)
def super_admin_recovery_verify(
    payload: SuperAdminRecoveryVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> SuperAdminAuthResponse:
    try:
        challenge = decode_super_admin_challenge_token(payload.challenge_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_challenge_token") from exc

    subject = challenge.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_challenge_token")
    try:
        admin_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_challenge_token") from exc

    admin = db.scalar(select(SuperAdminCredential).where(SuperAdminCredential.id == admin_id))
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="super_admin_not_found")
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super_admin_not_active")
    _enforce_mfa_verify_rate_limit(
        request=request,
        admin_id=admin.id,
        action="SUPER_ADMIN_LOGIN_RECOVERY_VERIFY",
        db=db,
    )

    code_hash = hash_recovery_code(payload.recovery_code)
    code_row = db.scalar(
        select(SuperAdminRecoveryCode).where(
            SuperAdminRecoveryCode.admin_id == admin.id,
            SuperAdminRecoveryCode.code_hash == code_hash,
            SuperAdminRecoveryCode.is_used.is_(False),
        )
    )
    if code_row is None:
        write_business_log(
            db=db,
            request=request,
            action="SUPER_ADMIN_LOGIN_RECOVERY_VERIFY",
            result="FAILED",
            role="SUPER_ADMIN",
            entity_type="SUPER_ADMIN",
            entity_id=str(admin.id),
            reason="恢复码无效",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="recovery_code_invalid")

    now = datetime.now(UTC)
    code_row.is_used = True
    code_row.used_at = now
    admin.last_login_at = now
    db.commit()
    db.refresh(admin)

    write_business_log(
        db=db,
        request=request,
        action="SUPER_ADMIN_LOGIN_RECOVERY_VERIFY",
        result="SUCCESS",
        role="SUPER_ADMIN",
        entity_type="SUPER_ADMIN",
        entity_id=str(admin.id),
        auto_commit=True,
    )
    return _build_super_admin_auth_response(admin)


@router.get("/me", response_model=SuperAdminOut)
def super_admin_me(
    request: Request,
    current_admin: SuperAdminCredential = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
) -> SuperAdminOut:
    write_business_log(
        db=db,
        request=request,
        action="SUPER_ADMIN_ME",
        result="SUCCESS",
        role="SUPER_ADMIN",
        entity_type="SUPER_ADMIN",
        entity_id=str(current_admin.id),
        auto_commit=True,
    )
    return _build_super_admin_out(current_admin)


@router.post("/refresh", response_model=SuperAdminAuthResponse)
def super_admin_refresh(
    request: Request,
    current_admin: SuperAdminCredential = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
) -> SuperAdminAuthResponse:
    write_business_log(
        db=db,
        request=request,
        action="SUPER_ADMIN_REFRESH_TOKEN",
        result="SUCCESS",
        role="SUPER_ADMIN",
        actor_user_id=current_admin.id,
        entity_type="SUPER_ADMIN",
        entity_id=str(current_admin.id),
        auto_commit=True,
    )
    return _build_super_admin_auth_response(current_admin)


@router.post("/logout", response_model=SuperAdminLogoutResponse)
def super_admin_logout(
    request: Request,
    current_admin: SuperAdminCredential = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
) -> SuperAdminLogoutResponse:
    write_business_log(
        db=db,
        request=request,
        action="SUPER_ADMIN_LOGOUT",
        result="SUCCESS",
        role="SUPER_ADMIN",
        actor_user_id=current_admin.id,
        entity_type="SUPER_ADMIN",
        entity_id=str(current_admin.id),
        auto_commit=True,
    )
    return SuperAdminLogoutResponse()
