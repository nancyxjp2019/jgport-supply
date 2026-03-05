import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any

from app.core.config import get_settings
from app.core.security import build_mock_openid

_LOGIN_CODE_OPENID_CACHE: dict[str, tuple[str, float]] = {}
_LOGIN_CODE_OPENID_CACHE_LOCK = Lock()
_LOGIN_CODE_OPENID_CACHE_TTL_SECONDS = 180


@dataclass
class WeChatResolveOpenIdError(Exception):
    status_code: int
    detail_code: str
    reason: str
    detail_json: dict[str, Any] | None = None


def resolve_openid_from_login_code(code: str) -> str:
    settings = get_settings()
    if settings.wechat_login_mode == "mock":
        return build_mock_openid(code)
    return _resolve_openid_official(code=code)


def cache_openid_by_login_code(*, code: str, openid: str, ttl_seconds: int = _LOGIN_CODE_OPENID_CACHE_TTL_SECONDS) -> None:
    if not code or not openid:
        return
    now = monotonic()
    expires_at = now + max(ttl_seconds, 0)
    with _LOGIN_CODE_OPENID_CACHE_LOCK:
        _cleanup_login_code_cache_locked(now=now)
        _LOGIN_CODE_OPENID_CACHE[code] = (openid, expires_at)


def pop_cached_openid_by_login_code(code: str) -> str | None:
    if not code:
        return None
    now = monotonic()
    with _LOGIN_CODE_OPENID_CACHE_LOCK:
        _cleanup_login_code_cache_locked(now=now)
        cached = _LOGIN_CODE_OPENID_CACHE.pop(code, None)
    if cached is None:
        return None
    openid, expires_at = cached
    if expires_at <= now:
        return None
    return openid


def _resolve_openid_official(code: str) -> str:
    settings = get_settings()
    app_id = settings.wechat_app_id.strip()
    app_secret = settings.wechat_app_secret.strip()
    if not app_id or not app_secret:
        raise WeChatResolveOpenIdError(
            status_code=500,
            detail_code="wechat_config_invalid",
            reason="微信登录配置缺失",
        )

    params = urllib.parse.urlencode(
        {
            "appid": app_id,
            "secret": app_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    base = settings.wechat_api_base.rstrip("/")
    url = f"{base}/sns/jscode2session?{params}"
    payload = _request_wechat_code2session(url=url, timeout_seconds=settings.wechat_api_timeout_seconds)

    errcode = payload.get("errcode")
    if errcode not in (None, 0, "0"):
        errcode_int = _safe_int(errcode)
        errmsg = str(payload.get("errmsg") or "").strip()
        if errcode_int in {40029, 40163}:
            raise WeChatResolveOpenIdError(
                status_code=400,
                detail_code="wechat_code_invalid",
                reason="微信登录凭证无效或已使用",
                detail_json={"wechat_errcode": errcode_int, "wechat_errmsg": errmsg},
            )
        if errcode_int == -1:
            raise WeChatResolveOpenIdError(
                status_code=503,
                detail_code="wechat_service_busy",
                reason="微信服务繁忙，请稍后重试",
                detail_json={"wechat_errcode": errcode_int, "wechat_errmsg": errmsg},
            )
        raise WeChatResolveOpenIdError(
            status_code=502,
            detail_code="wechat_service_error",
            reason="微信登录服务返回异常",
            detail_json={"wechat_errcode": errcode_int, "wechat_errmsg": errmsg},
        )

    openid = str(payload.get("openid") or "").strip()
    if not openid:
        raise WeChatResolveOpenIdError(
            status_code=502,
            detail_code="wechat_openid_missing",
            reason="微信登录返回缺少 openid",
            detail_json={"response_keys": sorted(list(payload.keys()))},
        )
    return openid


def _request_wechat_code2session(url: str, timeout_seconds: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise WeChatResolveOpenIdError(
            status_code=502,
            detail_code="wechat_service_http_error",
            reason="微信登录服务 HTTP 异常",
            detail_json={"http_status": exc.code},
        ) from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise WeChatResolveOpenIdError(
            status_code=503,
            detail_code="wechat_service_unavailable",
            reason="微信登录服务不可用",
        ) from exc

    try:
        parsed: dict[str, Any] = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise WeChatResolveOpenIdError(
            status_code=502,
            detail_code="wechat_service_invalid_response",
            reason="微信登录服务响应解析失败",
        ) from exc

    return parsed


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _cleanup_login_code_cache_locked(*, now: float) -> None:
    expired_codes = [code for code, (_, expires_at) in _LOGIN_CODE_OPENID_CACHE.items() if expires_at <= now]
    for code in expired_codes:
        _LOGIN_CODE_OPENID_CACHE.pop(code, None)
