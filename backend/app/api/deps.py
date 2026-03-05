from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.log_context import bind_user_context
from app.core.security import decode_access_token, decode_super_admin_access_token
from app.db.session import get_db
from app.models.super_admin import SuperAdminCredential
from app.models.user import User, UserRole, UserStatus

bearer_scheme = HTTPBearer(auto_error=False)
BRIDGE_ADMIN_USERNAME = "__super_admin_console_bridge__"
BRIDGE_ADMIN_DISPLAY_NAME = "后台管理中心桥接账号"


@dataclass
class AdminOperator:
    actor_id: int
    role: str
    user: User | None = None
    super_admin: SuperAdminCredential | None = None


def _ensure_bridge_admin_user(db: Session) -> User:
    row = db.scalar(select(User).where(User.username == BRIDGE_ADMIN_USERNAME))
    if row is None:
        row = User(
            username=BRIDGE_ADMIN_USERNAME,
            display_name=BRIDGE_ADMIN_DISPLAY_NAME,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(row)
        db.flush()
        db.commit()
        db.refresh(row)
        return row

    changed = False
    if row.role != UserRole.ADMIN:
        row.role = UserRole.ADMIN
        changed = True
    if row.status != UserStatus.ACTIVE:
        row.status = UserStatus.ACTIVE
        changed = True
    if not row.display_name:
        row.display_name = BRIDGE_ADMIN_DISPLAY_NAME
        changed = True
    if changed:
        db.commit()
        db.refresh(row)
    return row


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc

    if payload.get("type") == "super_admin_access":
        try:
            super_payload = decode_super_admin_access_token(credentials.credentials)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc
        subject = super_payload.get("sub")
        if not subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload")
        try:
            admin_id = int(subject)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload") from exc
        admin = db.scalar(select(SuperAdminCredential).where(SuperAdminCredential.id == admin_id))
        if admin is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="super_admin_not_found")
        if not admin.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super_admin_not_active")

        bridge_user = _ensure_bridge_admin_user(db)
        bind_user_context(admin.id, "SUPER_ADMIN")
        return bridge_user

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload")
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload") from exc

    user = db.scalar(select(User).where(User.id == user_id_int))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user_not_active")
    bind_user_context(user.id, user.role.value)
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
    return current_user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return current_user

    return checker


def get_current_super_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> SuperAdminCredential:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")

    try:
        payload = decode_super_admin_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload")
    try:
        admin_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload") from exc

    admin = db.scalar(select(SuperAdminCredential).where(SuperAdminCredential.id == admin_id))
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="super_admin_not_found")
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super_admin_not_active")

    bind_user_context(admin.id, "SUPER_ADMIN")
    return admin


def get_admin_operator(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AdminOperator:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        role = payload.get("role")
        token_type = payload.get("type")
        if token_type == "super_admin_access":
            raise ValueError("super_admin_token")
        if not subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload")
        user_id = int(subject)
        user = db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user_not_active")
        if user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
        if role and role != UserRole.ADMIN.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
        bind_user_context(user.id, user.role.value)
        return AdminOperator(actor_id=user.id, role=user.role.value, user=user)
    except (TypeError, ValueError):
        pass

    try:
        payload = decode_super_admin_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload")
    try:
        admin_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_payload") from exc

    admin = db.scalar(select(SuperAdminCredential).where(SuperAdminCredential.id == admin_id))
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="super_admin_not_found")
    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super_admin_not_active")

    bind_user_context(admin.id, "SUPER_ADMIN")
    bridge_user = _ensure_bridge_admin_user(db)
    return AdminOperator(actor_id=admin.id, role="SUPER_ADMIN", user=bridge_user, super_admin=admin)
