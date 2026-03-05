from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.log_context import bind_request_id, clear_user_context, reset_request_id
from app.core.logging_config import get_access_logger, get_system_logger


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        token = bind_request_id(request_id)
        clear_user_context()

        access_logger = get_access_logger()
        system_logger = get_system_logger()

        start = time.perf_counter()
        response: Response | None = None
        status_code = 500
        ip = request.client.host if request.client else None
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            system_logger.exception(
                "接口处理异常",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "ip": ip,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            access_logger.info(
                "接口访问",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "ip": ip,
                },
            )
            clear_user_context()
            reset_request_id(token)
