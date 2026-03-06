from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class WeChatCode2SessionResult:
    openid: str
    unionid: str | None
    session_key: str


@dataclass(frozen=True)
class WeChatLoginServiceError(Exception):
    status_code: int
    detail: str


def exchange_wechat_code2session(code: str) -> WeChatCode2SessionResult:
    normalized_code = str(code or "").strip()
    if not normalized_code:
        raise WeChatLoginServiceError(status_code=400, detail="微信登录凭证不能为空")

    settings = get_settings()
    if not settings.wechat_mini_app_id.strip() or not settings.wechat_mini_app_secret.strip():
        raise WeChatLoginServiceError(status_code=503, detail="微信登录配置缺失，请先配置 AppID 与 AppSecret")

    url = f"{settings.wechat_api_base.rstrip('/')}/sns/jscode2session"
    try:
        response = httpx.get(
            url,
            params={
                "appid": settings.wechat_mini_app_id.strip(),
                "secret": settings.wechat_mini_app_secret.strip(),
                "js_code": normalized_code,
                "grant_type": "authorization_code",
            },
            timeout=settings.wechat_api_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise WeChatLoginServiceError(status_code=502, detail="微信登录服务 HTTP 异常") from exc
    except httpx.TimeoutException as exc:
        raise WeChatLoginServiceError(status_code=503, detail="微信登录服务超时，请稍后重试") from exc
    except httpx.HTTPError as exc:
        raise WeChatLoginServiceError(status_code=503, detail="微信登录服务不可用，请稍后重试") from exc
    except ValueError as exc:
        raise WeChatLoginServiceError(status_code=502, detail="微信登录服务响应解析失败") from exc

    errcode = _safe_int(payload.get("errcode"))
    errmsg = str(payload.get("errmsg") or "").strip()
    if errcode in {40029, 40163}:
        raise WeChatLoginServiceError(status_code=400, detail="微信登录凭证无效或已使用")
    if errcode == -1:
        raise WeChatLoginServiceError(status_code=503, detail="微信服务繁忙，请稍后重试")
    if errcode not in {None, 0}:
        raise WeChatLoginServiceError(
            status_code=502,
            detail=f"微信登录服务返回异常{f'：{errmsg}' if errmsg else ''}",
        )

    openid = str(payload.get("openid") or "").strip()
    session_key = str(payload.get("session_key") or "").strip()
    unionid = str(payload.get("unionid") or "").strip() or None
    if not openid or not session_key:
        raise WeChatLoginServiceError(status_code=502, detail="微信登录返回缺少 openid 或 session_key")

    return WeChatCode2SessionResult(
        openid=openid,
        unionid=unionid,
        session_key=session_key,
    )


def _safe_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
