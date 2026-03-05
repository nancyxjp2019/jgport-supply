import hashlib
import hmac
import secrets
import string
import struct
from base64 import b32decode, b32encode
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def build_mock_openid(code: str) -> str:
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()[:24]
    return f"mock_openid_{digest}"


def generate_activation_code(length: int = 24) -> str:
    # 生成一次性激活链接使用的随机码，仅允许字母和数字，避免包含连字符。
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_password(plain_password: str) -> str:
    return password_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


def generate_totp_secret(length: int = 20) -> str:
    raw = secrets.token_bytes(length)
    return b32encode(raw).decode("utf-8").rstrip("=")


def build_totp_provisioning_uri(secret: str, account_name: str, issuer: str) -> str:
    account = quote(account_name)
    safe_issuer = quote(issuer)
    return f"otpauth://totp/{safe_issuer}:{account}?secret={secret}&issuer={safe_issuer}&algorithm=SHA1&digits=6&period=30"


def _normalize_base32_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    missing_padding = (-len(normalized)) % 8
    if missing_padding:
        normalized += "=" * missing_padding
    return b32decode(normalized.encode("utf-8"), casefold=True)


def _build_totp_code(secret: str, for_time: int, interval_seconds: int = 30, digits: int = 6) -> str:
    counter = int(for_time // interval_seconds)
    key = _normalize_base32_secret(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    code = binary % (10**digits)
    return str(code).zfill(digits)


def verify_totp_code(secret: str, code: str, window: int = 1, interval_seconds: int = 30) -> bool:
    text_code = str(code).strip()
    if not text_code.isdigit() or len(text_code) != 6:
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    for delta in range(-window, window + 1):
        expected = _build_totp_code(secret, now + delta * interval_seconds, interval_seconds=interval_seconds, digits=6)
        if hmac.compare_digest(expected, text_code):
            return True
    return False


def build_totp_code_for_current_time(secret: str) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    return _build_totp_code(secret, now, interval_seconds=30, digits=6)


def generate_recovery_codes(count: int = 8) -> list[str]:
    result: list[str] = []
    while len(result) < count:
        raw = secrets.token_hex(4).upper()
        code = f"{raw[:4]}-{raw[4:]}"
        if code not in result:
            result.append(code)
    return result


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expires_at = datetime.now(timezone.utc) + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid_token") from exc


def create_super_admin_challenge_token(admin_id: int, minutes: int = 5) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=minutes)
    expires_at = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {
        "sub": str(admin_id),
        "type": "super_admin_challenge",
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_super_admin_challenge_token(token: str) -> dict[str, Any]:
    payload = decode_access_token(token)
    if payload.get("type") != "super_admin_challenge":
        raise ValueError("invalid_super_admin_challenge_token")
    return payload


def create_super_admin_access_token(subject: str) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expires_at = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "super_admin_access",
        "role": "SUPER_ADMIN",
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_super_admin_access_token(token: str) -> dict[str, Any]:
    payload = decode_access_token(token)
    if payload.get("type") != "super_admin_access":
        raise ValueError("invalid_super_admin_access_token")
    return payload
