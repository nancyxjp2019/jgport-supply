from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, status

from app.core.auth_actor import AuthenticatedActor
from app.core.config import get_settings

TOKEN_PREFIX = "m1"
TOKEN_EXPIRES_IN_SECONDS = 7200


def issue_direct_auth_token(actor: AuthenticatedActor, *, expires_in_seconds: int = TOKEN_EXPIRES_IN_SECONDS) -> str:
    settings = get_settings()
    payload = asdict(actor) | {"exp": int(time.time()) + expires_in_seconds}
    payload_segment = _encode_segment(payload)
    signature_segment = _sign_segment(payload_segment, settings.direct_auth_token_secret)
    return f"{TOKEN_PREFIX}.{payload_segment}.{signature_segment}"


def verify_direct_auth_token(token: str) -> AuthenticatedActor:
    settings = get_settings()
    try:
        prefix, payload_segment, signature_segment = token.split(".", 2)
    except ValueError as exc:
        raise _build_invalid_token_error("登录令牌格式不正确") from exc
    if prefix != TOKEN_PREFIX:
        raise _build_invalid_token_error("登录令牌版本不支持")

    expected_signature = _sign_segment(payload_segment, settings.direct_auth_token_secret)
    if not hmac.compare_digest(signature_segment, expected_signature):
        raise _build_invalid_token_error("登录令牌签名校验失败")

    try:
        payload = json.loads(_decode_segment(payload_segment))
    except (json.JSONDecodeError, ValueError) as exc:
        raise _build_invalid_token_error("登录令牌内容解析失败") from exc

    required_fields = {"user_id", "role_code", "company_id", "company_type", "client_type", "exp"}
    if not required_fields.issubset(payload):
        raise _build_invalid_token_error("登录令牌字段不完整")
    if int(payload["exp"]) <= int(time.time()):
        raise _build_invalid_token_error("登录令牌已过期，请重新登录")

    return AuthenticatedActor(
        user_id=str(payload["user_id"]),
        role_code=str(payload["role_code"]),
        company_id=str(payload["company_id"]) if payload["company_id"] is not None else None,
        company_type=str(payload["company_type"]),
        client_type=str(payload["client_type"]),
    )


def _encode_segment(payload: dict[str, object]) -> str:
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode("ascii")


def _decode_segment(segment: str) -> str:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(f"{segment}{padding}".encode("ascii")).decode("utf-8")


def _sign_segment(segment: str, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), segment.encode("ascii"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")


def _build_invalid_token_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
