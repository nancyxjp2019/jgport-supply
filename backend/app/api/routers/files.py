from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.master_data import Warehouse
from app.models.user import User, UserRole
from app.models.v5_domain import FileAsset, FileAssetLink, PurchaseContract, PurchaseOrderV5, SalesContract, SalesOrderV5
from app.schemas.file_asset import FileUploadOut
from app.services.business_log_service import write_business_log
from app.services.file_storage_service import read_file_bytes_by_key, save_upload_file
from app.services.v5_file_asset_service import ensure_file_asset
from app.services.v5_report_service import can_access_report_export_file

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/object/{file_key:path}")
def get_file_object(
    file_key: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    asset = _ensure_file_read_permission(
        db=db,
        current_user=current_user,
        file_key=file_key,
    )
    content, content_type = read_file_bytes_by_key(file_key)
    write_business_log(
        db=db,
        request=request,
        action="FILE_READ",
        result="SUCCESS",
        user=current_user,
        entity_type="FILE",
        entity_id=file_key,
        auto_commit=True,
    )
    return Response(
        content=content,
        media_type=content_type or "application/octet-stream",
        headers=_build_file_download_headers(file_key=file_key, asset=asset),
    )


@router.post("/upload", response_model=FileUploadOut)
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileUploadOut:
    result = save_upload_file(file=file, category=category)
    ensure_file_asset(
        db,
        file_key=result.file_key,
        business_type=f"upload:{str(category or 'general').strip() or 'general'}",
        current_user=current_user,
        file_name=result.original_filename,
    )
    write_business_log(
        db=db,
        request=request,
        action="FILE_UPLOAD",
        result="SUCCESS",
        user=current_user,
        entity_type="FILE",
        entity_id=result.file_key,
        detail_json={
            "category": category,
            "file_url": result.file_url,
            "size_bytes": result.size_bytes,
            "content_type": result.content_type,
        },
        auto_commit=True,
    )
    return result


def _ensure_file_read_permission(db: Session, current_user: User, file_key: str) -> FileAsset:
    asset = _get_v5_file_asset(db=db, file_key=file_key)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    if asset.business_type == "report_export":
        if can_access_report_export_file(db=db, current_user=current_user, file_key=file_key):
            return asset
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    if _can_access_v5_file(db=db, current_user=current_user, asset=asset):
        return asset
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


def _build_file_download_headers(*, file_key: str, asset: FileAsset) -> dict[str, str]:
    download_name = _resolve_download_file_name(file_key=file_key, asset=asset)
    encoded_name = quote(download_name, safe="")
    ascii_name = _build_ascii_download_name(download_name)
    return {
        "Content-Disposition": f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}',
        "X-File-Name": encoded_name,
        "Access-Control-Expose-Headers": "Content-Disposition, X-File-Name, Content-Type",
        "Cache-Control": "no-store",
    }


def _resolve_download_file_name(*, file_key: str, asset: FileAsset) -> str:
    file_name = str(getattr(asset, "file_name", "") or "").strip()
    if file_name:
        return file_name
    fallback_name = PurePosixPath(str(file_key or "").strip()).name
    return fallback_name or "download"


def _build_ascii_download_name(file_name: str) -> str:
    path_name = PurePosixPath(str(file_name or "").strip())
    suffix = path_name.suffix if path_name.suffix.isascii() else ""
    stem = path_name.stem or "download"
    normalized_stem = "".join(ch for ch in stem if ch.isascii() and (ch.isalnum() or ch in {"-", "_", "."})).strip("._-")
    if not normalized_stem:
        normalized_stem = "download"
    return f"{normalized_stem}{suffix}" if suffix else normalized_stem


def _get_v5_file_asset(db: Session, *, file_key: str) -> FileAsset | None:
    normalized_key = str(file_key or "").strip().strip("/")
    if not normalized_key:
        return None
    return db.scalar(select(FileAsset).where(FileAsset.file_key == normalized_key))


def _can_access_v5_file(db: Session, *, current_user: User, asset: FileAsset) -> bool:
    if asset.uploaded_by == current_user.id:
        return True
    if current_user.role in {UserRole.ADMIN, UserRole.OPERATOR, UserRole.FINANCE}:
        return True
    if current_user.role == UserRole.CUSTOMER:
        if current_user.company_id is None:
            return False
        return _customer_has_v5_sales_order_file(db=db, company_id=current_user.company_id, asset_id=asset.id) or _customer_has_v5_sales_contract_file(
            db=db,
            company_id=current_user.company_id,
            asset_id=asset.id,
        )
    if current_user.role == UserRole.SUPPLIER:
        if current_user.company_id is None:
            return False
        return _supplier_has_v5_purchase_order_file(
            db=db,
            company_id=current_user.company_id,
            asset_id=asset.id,
        ) or _supplier_has_v5_purchase_contract_file(
            db=db,
            company_id=current_user.company_id,
            asset_id=asset.id,
        )
    if current_user.role == UserRole.WAREHOUSE:
        if current_user.company_id is None:
            return False
        return _warehouse_has_v5_purchase_order_file(db=db, company_id=current_user.company_id, asset_id=asset.id)
    return False


def _customer_has_v5_sales_order_file(db: Session, *, company_id: int, asset_id: int) -> bool:
    direct_order = db.scalar(
        select(SalesOrderV5.id).where(
            SalesOrderV5.customer_company_id == company_id,
            SalesOrderV5.customer_payment_receipt_file_id == asset_id,
        )
    )
    if direct_order is not None:
        return True
    linked_order = db.scalar(
        select(SalesOrderV5.id)
        .join(
            FileAssetLink,
            (FileAssetLink.entity_type == "SALES_ORDER") & (FileAssetLink.entity_id == SalesOrderV5.id),
        )
        .where(
            SalesOrderV5.customer_company_id == company_id,
            FileAssetLink.file_asset_id == asset_id,
        )
    )
    return linked_order is not None


def _customer_has_v5_sales_contract_file(db: Session, *, company_id: int, asset_id: int) -> bool:
    direct_contract = db.scalar(
        select(SalesContract.id).where(
            SalesContract.customer_company_id == company_id,
            (SalesContract.signed_contract_file_id == asset_id) | (SalesContract.deposit_receipt_file_id == asset_id),
        )
    )
    if direct_contract is not None:
        return True
    linked_contract = db.scalar(
        select(SalesContract.id)
        .join(
            FileAssetLink,
            (FileAssetLink.entity_type == "SALES_CONTRACT") & (FileAssetLink.entity_id == SalesContract.id),
        )
        .where(
            SalesContract.customer_company_id == company_id,
            FileAssetLink.file_asset_id == asset_id,
        )
    )
    return linked_contract is not None


def _supplier_has_v5_purchase_order_file(db: Session, *, company_id: int, asset_id: int) -> bool:
    return db.scalar(
        select(PurchaseOrderV5.id).where(
            PurchaseOrderV5.supplier_company_id == company_id,
            (
                (PurchaseOrderV5.delivery_instruction_pdf_file_id == asset_id)
                | (PurchaseOrderV5.supplier_delivery_doc_file_id == asset_id)
                | (PurchaseOrderV5.outbound_doc_file_id == asset_id)
            ),
        )
    ) is not None


def _supplier_has_v5_purchase_contract_file(db: Session, *, company_id: int, asset_id: int) -> bool:
    direct_contract = db.scalar(
        select(PurchaseContract.id).where(
            PurchaseContract.supplier_company_id == company_id,
            (PurchaseContract.signed_contract_file_id == asset_id) | (PurchaseContract.deposit_receipt_file_id == asset_id),
        )
    )
    if direct_contract is not None:
        return True
    linked_contract = db.scalar(
        select(PurchaseContract.id)
        .join(
            FileAssetLink,
            (FileAssetLink.entity_type == "PURCHASE_CONTRACT") & (FileAssetLink.entity_id == PurchaseContract.id),
        )
        .where(
            PurchaseContract.supplier_company_id == company_id,
            FileAssetLink.file_asset_id == asset_id,
        )
    )
    return linked_contract is not None


def _warehouse_has_v5_purchase_order_file(db: Session, *, company_id: int, asset_id: int) -> bool:
    warehouse_ids = db.scalars(select(Warehouse.id).where(Warehouse.company_id == company_id)).all()
    if not warehouse_ids:
        return False
    return db.scalar(
        select(PurchaseOrderV5.id).where(
            PurchaseOrderV5.warehouse_id.in_(warehouse_ids),
            (
                (PurchaseOrderV5.delivery_instruction_pdf_file_id == asset_id)
                | (PurchaseOrderV5.supplier_delivery_doc_file_id == asset_id)
                | (PurchaseOrderV5.outbound_doc_file_id == asset_id)
            ),
        )
    ) is not None
