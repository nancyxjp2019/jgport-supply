from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.file_asset import FileUploadOut

UPLOAD_ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".pdf",
    ".xls",
    ".xlsx",
}


@dataclass
class StoredFileMeta:
    file_key: str
    size_bytes: int
    content_type: str | None


def save_upload_file(file: UploadFile, category: str = "general") -> FileUploadOut:
    suffix = _build_suffix(file.filename, allowed_extensions=UPLOAD_ALLOWED_EXTENSIONS)
    if not suffix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件类型不支持，仅允许 jpg/jpeg/png/webp/pdf/xls/xlsx",
        )

    settings = get_settings()
    max_size_bytes = settings.upload_max_size_mb * 1024 * 1024
    content = file.file.read(max_size_bytes + 1)
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件过大，超过 {settings.upload_max_size_mb}MB 限制",
        )

    file_key = build_storage_key(category=category, suffix=suffix)
    content_type = (file.content_type or "").strip() or mimetypes.guess_type(file.filename or "")[0]
    return save_binary_file(
        content=content,
        file_key=file_key,
        content_type=content_type,
        original_filename=file.filename or "",
        allowed_extensions=UPLOAD_ALLOWED_EXTENSIONS,
        invalid_extension_detail="文件类型不支持，仅允许 jpg/jpeg/png/webp/pdf/xls/xlsx",
    )


def save_binary_file(
    *,
    content: bytes,
    file_key: str,
    content_type: str | None,
    original_filename: str,
    allowed_extensions: set[str] | None = None,
    invalid_extension_detail: str = "文件类型不支持，仅允许 jpg/jpeg/png/webp/pdf/xls/xlsx",
) -> FileUploadOut:
    settings = get_settings()
    storage_backend = settings.file_storage_backend.strip().lower()
    normalized_key = _normalize_file_key(file_key)
    suffix = Path(normalized_key).suffix.lower()
    normalized_allowed_extensions = {str(item or "").lower() for item in (allowed_extensions or UPLOAD_ALLOWED_EXTENSIONS)}
    if suffix not in normalized_allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_extension_detail,
        )

    max_size_bytes = settings.upload_max_size_mb * 1024 * 1024
    size_bytes = len(content)
    if size_bytes > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件过大，超过 {settings.upload_max_size_mb}MB 限制",
        )

    if storage_backend == "local":
        _save_local_bytes(file_key=normalized_key, content=content)
    elif storage_backend == "oss":
        _save_oss_bytes(file_key=normalized_key, content=content, content_type=content_type)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="file_storage_backend 配置无效，仅支持 local 或 oss",
        )

    return FileUploadOut(
        file_url=build_file_url_by_key(normalized_key),
        file_key=normalized_key,
        storage=storage_backend,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )


def build_storage_key(category: str, suffix: str) -> str:
    settings = get_settings()
    safe_category = "".join(ch for ch in category.lower() if ch.isalnum() or ch in {"-", "_"}) or "general"
    date_path = datetime.now().strftime("%Y%m%d")
    file_name = f"{uuid4().hex}{suffix.lower()}"
    relative_path = f"{safe_category}/{date_path}/{file_name}"
    if settings.file_storage_backend.strip().lower() == "oss":
        prefix = settings.oss_prefix.strip().strip("/")
        if prefix:
            relative_path = f"{prefix}/{relative_path}"
    return _normalize_file_key(relative_path)


def build_file_url_by_key(file_key: str) -> str:
    settings = get_settings()
    normalized_key = _normalize_file_key(file_key)
    storage_backend = settings.file_storage_backend.strip().lower()
    if storage_backend == "local":
        base_url = settings.local_upload_base_url.rstrip("/")
        return f"{base_url}/{normalized_key}"
    if storage_backend == "oss":
        oss_base = settings.oss_base_url.strip().rstrip("/")
        if oss_base:
            return f"{oss_base}/{normalized_key}"
        api_prefix = settings.api_prefix.rstrip("/")
        return f"{api_prefix}/files/object/{quote(normalized_key, safe='/')}"
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="file_storage_backend 配置无效，仅支持 local 或 oss",
    )


def build_protected_file_url_by_key(file_key: str) -> str:
    settings = get_settings()
    normalized_key = _normalize_file_key(file_key)
    api_prefix = settings.api_prefix.rstrip("/")
    return f"{api_prefix}/files/object/{quote(normalized_key, safe='/')}"


def resolve_file_key_from_url(file_url: str) -> str:
    settings = get_settings()
    text = (file_url or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="transport_attachment_url_invalid")

    parsed = urlparse(text)
    path = parsed.path or text
    if not path.startswith("/"):
        path = f"/{path}"

    local_prefix = f"{settings.local_upload_base_url.rstrip('/')}/"
    if path.startswith(local_prefix):
        return _normalize_file_key(path[len(local_prefix) :])

    object_prefixes = [
        f"{settings.api_prefix.rstrip('/')}/files/object/",
        "/api/v1/files/object/",
        "/files/object/",
    ]
    for prefix in object_prefixes:
        if path.startswith(prefix):
            return _normalize_file_key(path[len(prefix) :])

    oss_base = settings.oss_base_url.strip().rstrip("/")
    if oss_base and text.startswith(f"{oss_base}/"):
        cleaned = text[len(oss_base) + 1 :]
        cleaned = cleaned.split("?", 1)[0].split("#", 1)[0]
        return _normalize_file_key(cleaned)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="transport_attachment_url_invalid")


def get_file_metadata_by_key(file_key: str) -> StoredFileMeta:
    settings = get_settings()
    storage_backend = settings.file_storage_backend.strip().lower()
    normalized_key = _normalize_file_key(file_key)
    if storage_backend == "local":
        return _get_local_file_metadata(normalized_key)
    if storage_backend == "oss":
        return _get_oss_file_metadata(normalized_key)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="file_storage_backend 配置无效，仅支持 local 或 oss",
    )


def read_file_bytes_by_key(file_key: str) -> tuple[bytes, str | None]:
    settings = get_settings()
    storage_backend = settings.file_storage_backend.strip().lower()
    normalized_key = _normalize_file_key(file_key)
    if storage_backend == "local":
        return _read_local_file_bytes(normalized_key)
    if storage_backend == "oss":
        return _read_oss_file_bytes(normalized_key)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="file_storage_backend 配置无效，仅支持 local 或 oss",
    )


def _resolve_local_upload_root() -> Path:
    settings = get_settings()
    upload_dir = Path(settings.local_upload_dir).expanduser()
    if not upload_dir.is_absolute():
        backend_root = Path(__file__).resolve().parents[2]
        upload_dir = backend_root / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir.resolve()


def _build_suffix(filename: str | None, *, allowed_extensions: set[str]) -> str:
    if not filename:
        return ""
    suffix = Path(filename).suffix.lower()
    if suffix and suffix in allowed_extensions:
        return suffix
    return ""


def _normalize_file_key(file_key: str) -> str:
    text = (file_key or "").strip().strip("/")
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_file_key")
    if "\\" in text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_file_key")
    path = PurePosixPath(text)
    if path.is_absolute():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_file_key")
    parts = list(path.parts)
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_file_key")
    return "/".join(parts)


def _resolve_local_file_path(file_key: str) -> Path:
    root = _resolve_local_upload_root()
    target = (root / file_key).resolve()
    if target != root and root not in target.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_file_key")
    return target


def _save_local_bytes(*, file_key: str, content: bytes) -> None:
    target_path = _resolve_local_file_path(file_key)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(content)


def _get_local_file_metadata(file_key: str) -> StoredFileMeta:
    file_path = _resolve_local_file_path(file_key)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found")
    content_type = mimetypes.guess_type(str(file_path))[0]
    return StoredFileMeta(
        file_key=file_key,
        size_bytes=file_path.stat().st_size,
        content_type=content_type,
    )


def _read_local_file_bytes(file_key: str) -> tuple[bytes, str | None]:
    file_path = _resolve_local_file_path(file_key)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found")
    return file_path.read_bytes(), mimetypes.guess_type(str(file_path))[0]


def _build_oss_bucket():
    settings = get_settings()
    app_id = settings.oss_access_key_id.strip()
    app_secret = settings.oss_access_key_secret.strip()
    endpoint = settings.oss_endpoint.strip()
    bucket_name = settings.oss_bucket_name.strip()
    if not app_id or not app_secret or not endpoint or not bucket_name:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="oss_config_invalid")

    try:
        import oss2  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="oss_sdk_not_installed",
        ) from exc

    endpoint_url = endpoint if endpoint.startswith("http://") or endpoint.startswith("https://") else f"https://{endpoint}"
    auth = oss2.Auth(app_id, app_secret)
    return oss2, oss2.Bucket(auth, endpoint_url, bucket_name)


def _save_oss_bytes(*, file_key: str, content: bytes, content_type: str | None) -> None:
    oss2, bucket = _build_oss_bucket()
    headers: dict[str, str] = {}
    if content_type:
        headers["Content-Type"] = content_type
    try:
        bucket.put_object(file_key, content, headers=headers)
    except oss2.exceptions.OssError as exc:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="oss_upload_failed",
        ) from exc


def _get_oss_file_metadata(file_key: str) -> StoredFileMeta:
    oss2, bucket = _build_oss_bucket()
    try:
        result = bucket.head_object(file_key)
    except oss2.exceptions.NoSuchKey as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found") from exc
    except oss2.exceptions.OssError as exc:  # type: ignore[attr-defined]
        if getattr(exc, "status", None) == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found") from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="oss_metadata_failed",
        ) from exc

    size = int(result.headers.get("Content-Length") or result.content_length or 0)
    content_type = result.headers.get("Content-Type")
    return StoredFileMeta(file_key=file_key, size_bytes=size, content_type=content_type)


def _read_oss_file_bytes(file_key: str) -> tuple[bytes, str | None]:
    oss2, bucket = _build_oss_bucket()
    try:
        result = bucket.get_object(file_key)
        content = result.read()
    except oss2.exceptions.NoSuchKey as exc:  # type: ignore[attr-defined]
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found") from exc
    except oss2.exceptions.OssError as exc:  # type: ignore[attr-defined]
        if getattr(exc, "status", None) == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found") from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="oss_read_failed",
        ) from exc

    content_type = result.headers.get("Content-Type")
    return content, content_type
