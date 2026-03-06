from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings

ALLOWED_CLIENT_TYPES = {"admin_web", "miniprogram"}


@dataclass(frozen=True)
class AuthenticatedActor:
    user_id: str
    role_code: str
    company_id: str | None
    company_type: str
    client_type: str


def get_current_actor(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_role_code: str | None = Header(default=None, alias="X-Role-Code"),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_company_type: str | None = Header(default=None, alias="X-Company-Type"),
    x_client_type: str | None = Header(default=None, alias="X-Client-Type"),
    x_auth_secret: str | None = Header(default=None, alias="X-Auth-Secret"),
) -> AuthenticatedActor:
    settings = get_settings()
    if not all([x_user_id, x_role_code, x_company_type, x_client_type, x_auth_secret]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证身份，禁止访问",
        )
    if x_auth_secret != settings.auth_proxy_shared_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="服务端身份校验失败",
        )
    if x_client_type not in ALLOWED_CLIENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="来源端类型不合法",
        )
    return AuthenticatedActor(
        user_id=x_user_id,
        role_code=x_role_code,
        company_id=x_company_id,
        company_type=x_company_type,
        client_type=x_client_type,
    )


def require_actor(
    *,
    allowed_roles: set[str],
    allowed_client_types: set[str],
    allowed_company_types: set[str],
) -> Callable[[AuthenticatedActor], AuthenticatedActor]:
    def dependency(actor: AuthenticatedActor = Depends(get_current_actor)) -> AuthenticatedActor:
        if actor.role_code not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前角色无权访问该接口",
            )
        if actor.client_type not in allowed_client_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前端类型无权访问该接口",
            )
        if actor.company_type not in allowed_company_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前公司范围无权访问该接口",
            )
        return actor

    return dependency
