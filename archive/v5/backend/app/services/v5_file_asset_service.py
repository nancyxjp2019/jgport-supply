from __future__ import annotations

from pathlib import PurePosixPath

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.models.v5_domain import FileAsset, FileAssetLink, StorageBackend
from app.services.file_storage_service import build_protected_file_url_by_key, get_file_metadata_by_key


def ensure_file_asset(
    db: Session,
    *,
    file_key: str,
    business_type: str,
    current_user: User,
    file_name: str | None = None,
) -> FileAsset:
    row = db.scalar(select(FileAsset).where(FileAsset.file_key == file_key))
    if row is not None:
        normalized_file_name = str(file_name or "").strip()
        if normalized_file_name and row.file_name == PurePosixPath(file_key).name and row.file_name != normalized_file_name:
            row.file_name = normalized_file_name
        return row

    metadata = get_file_metadata_by_key(file_key)
    settings = get_settings()
    storage_backend = StorageBackend.OSS if settings.file_storage_backend.strip().lower() == "oss" else StorageBackend.LOCAL
    normalized_file_name = str(file_name or "").strip() or PurePosixPath(file_key).name
    row = FileAsset(
        file_key=file_key,
        business_type=business_type,
        file_name=normalized_file_name,
        content_type=metadata.content_type or "application/octet-stream",
        file_size_bytes=metadata.size_bytes,
        storage_backend=storage_backend,
        uploaded_by=current_user.id,
    )
    db.add(row)
    db.flush()
    return row


def replace_file_asset_links(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    field_name: str,
    file_asset_ids: list[int],
) -> None:
    db.execute(
        delete(FileAssetLink).where(
            FileAssetLink.entity_type == entity_type,
            FileAssetLink.entity_id == entity_id,
            FileAssetLink.field_name == field_name,
        )
    )
    for index, file_asset_id in enumerate(file_asset_ids):
        db.add(
            FileAssetLink(
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                file_asset_id=file_asset_id,
                sort_no=index,
            )
        )


def list_file_keys_by_link(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    field_name: str,
) -> list[str]:
    rows = db.execute(
        select(FileAsset.file_key)
        .join(FileAssetLink, FileAssetLink.file_asset_id == FileAsset.id)
        .where(
            FileAssetLink.entity_type == entity_type,
            FileAssetLink.entity_id == entity_id,
            FileAssetLink.field_name == field_name,
        )
        .order_by(FileAssetLink.sort_no.asc(), FileAssetLink.id.asc())
    ).all()
    return [row.file_key for row in rows]


def build_protected_file_urls(file_keys: list[str]) -> list[str]:
    return [build_protected_file_url_by_key(item) for item in file_keys]
