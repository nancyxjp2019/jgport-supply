from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_ctx: ContextVar[int | None] = ContextVar("user_id", default=None)
_role_ctx: ContextVar[str | None] = ContextVar("role", default=None)


def bind_request_id(request_id: str) -> Token[str | None]:
    return _request_id_ctx.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id_ctx.reset(token)


def bind_user_context(user_id: int | None, role: str | None) -> None:
    _user_id_ctx.set(user_id)
    _role_ctx.set(role)


def clear_user_context() -> None:
    _user_id_ctx.set(None)
    _role_ctx.set(None)


def get_log_context() -> dict[str, Any]:
    return {
        "request_id": _request_id_ctx.get(),
        "user_id": _user_id_ctx.get(),
        "role": _role_ctx.get(),
    }
