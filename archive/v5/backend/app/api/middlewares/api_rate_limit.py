from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.rate_limit import InMemorySlidingWindowRateLimiter


@dataclass(frozen=True)
class ApiRateLimitRule:
    path_prefix: str
    method: str
    max_requests: int
    window_seconds: int
    scope: str


_RATE_LIMIT_RULES: tuple[ApiRateLimitRule, ...] = (
    ApiRateLimitRule(
        path_prefix="/api/v1/admin/auth/login",
        method="POST",
        max_requests=20,
        window_seconds=60,
        scope="admin_login",
    ),
    ApiRateLimitRule(
        path_prefix="/api/v1/auth/wechat/login",
        method="POST",
        max_requests=60,
        window_seconds=60,
        scope="wechat_login",
    ),
    ApiRateLimitRule(
        path_prefix="/api/v1/auth/wechat/bind",
        method="POST",
        max_requests=30,
        window_seconds=60,
        scope="wechat_bind",
    ),
    ApiRateLimitRule(
        path_prefix="/api/v1/files/upload",
        method="POST",
        max_requests=40,
        window_seconds=60,
        scope="file_upload",
    ),
)


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP 的接口限流中间件，用于拦截公网高频探测。"""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._limiters = {
            rule.scope: InMemorySlidingWindowRateLimiter(
                max_requests=rule.max_requests,
                window_seconds=rule.window_seconds,
            )
            for rule in _RATE_LIMIT_RULES
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        rule = self._match_rule(request)
        if rule is not None:
            client_ip = _extract_client_ip(request)
            key = f"{rule.scope}:{client_ip}"
            result = self._limiters[rule.scope].hit(key)
            if not result.allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "too_many_requests"},
                    headers={"Retry-After": str(result.retry_after_seconds)},
                )
        return await call_next(request)

    def _match_rule(self, request: Request) -> ApiRateLimitRule | None:
        path = request.url.path
        method = request.method.upper()
        for rule in _RATE_LIMIT_RULES:
            if method == rule.method and path.startswith(rule.path_prefix):
                return rule
        return None


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
