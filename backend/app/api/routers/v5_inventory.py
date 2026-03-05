from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.v5_domain import PurchaseStockInStatus
from app.schemas.v5_inventory import (
    InventoryAdjustmentCreateRequest,
    InventoryAdjustmentOut,
    InventoryMovementOut,
    InventorySummaryOut,
    PurchaseStockInConfirmRequest,
    PurchaseStockInDetailOut,
    PurchaseStockInListItemOut,
)
from app.services.business_log_service import write_business_log
from app.services.v5_inventory_service import (
    confirm_purchase_stock_in,
    create_inventory_adjustment,
    get_purchase_stock_in_with_scope,
    list_inventory_adjustments,
    list_inventory_movements,
    list_purchase_stock_ins,
    serialize_inventory_adjustment_list,
    serialize_inventory_movement_list,
    serialize_purchase_stock_in_detail,
    serialize_purchase_stock_in_list,
    summarize_inventory,
)

router = APIRouter(tags=["v5-inventory"])


@router.get("/purchase-stock-ins", response_model=list[PurchaseStockInListItemOut])
def list_v5_purchase_stock_ins(
    request: Request,
    status_value: PurchaseStockInStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[PurchaseStockInListItemOut]:
    rows = list_purchase_stock_ins(db=db, status_value=status_value, page=page, page_size=page_size)
    result = serialize_purchase_stock_in_list(db=db, rows=rows)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_STOCK_IN_LIST",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_STOCK_IN",
        detail_json={"count": len(result)},
        auto_commit=True,
    )
    return result


@router.get("/purchase-stock-ins/{stock_in_id}", response_model=PurchaseStockInDetailOut)
def get_v5_purchase_stock_in(
    stock_in_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseStockInDetailOut:
    row = get_purchase_stock_in_with_scope(db=db, stock_in_id=stock_in_id, current_user=current_user)
    result = serialize_purchase_stock_in_detail(db=db, row=row)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_STOCK_IN_DETAIL",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_STOCK_IN",
        entity_id=str(row.id),
        auto_commit=True,
    )
    return result


@router.patch("/purchase-stock-ins/{stock_in_id}/confirm", response_model=PurchaseStockInDetailOut)
def confirm_v5_purchase_stock_in(
    stock_in_id: int,
    payload: PurchaseStockInConfirmRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseStockInDetailOut:
    row = get_purchase_stock_in_with_scope(db=db, stock_in_id=stock_in_id, current_user=current_user)
    before_status = row.status.value
    row = confirm_purchase_stock_in(
        db=db,
        purchase_stock_in=row,
        payload=payload,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_STOCK_IN_CONFIRM",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_STOCK_IN",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
        detail_json={
            "warehouse_id": payload.warehouse_id,
            "product_id": payload.product_id,
            "stock_in_qty": payload.stock_in_qty,
        },
    )
    db.commit()
    db.refresh(row)
    return serialize_purchase_stock_in_detail(db=db, row=row)


@router.get("/inventory-adjustments", response_model=list[InventoryAdjustmentOut])
def list_v5_inventory_adjustments(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[InventoryAdjustmentOut]:
    rows = list_inventory_adjustments(db=db, page=page, page_size=page_size)
    result = serialize_inventory_adjustment_list(db=db, rows=rows)
    write_business_log(
        db=db,
        request=request,
        action="V5_INVENTORY_ADJUSTMENT_LIST",
        result="SUCCESS",
        user=current_user,
        entity_type="INVENTORY_ADJUSTMENT",
        detail_json={"count": len(result)},
        auto_commit=True,
    )
    return result


@router.post("/inventory-adjustments", response_model=InventoryAdjustmentOut)
def create_v5_inventory_adjustment(
    payload: InventoryAdjustmentCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> InventoryAdjustmentOut:
    row = create_inventory_adjustment(db=db, payload=payload, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_INVENTORY_ADJUSTMENT_CREATE",
        result="SUCCESS",
        user=current_user,
        entity_type="INVENTORY_ADJUSTMENT",
        entity_id=str(row.id),
        detail_json={
            "warehouse_id": payload.warehouse_id,
            "product_id": payload.product_id,
            "adjust_type": payload.adjust_type.value,
            "adjust_qty": payload.adjust_qty,
        },
    )
    db.commit()
    db.refresh(row)
    return serialize_inventory_adjustment_list(db=db, rows=[row])[0]


@router.get("/inventory/summary", response_model=InventorySummaryOut)
def get_v5_inventory_summary(
    request: Request,
    low_stock_threshold: float = Query(default=10.0, ge=0),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> InventorySummaryOut:
    result = summarize_inventory(
        db=db,
        current_user=current_user,
        low_stock_threshold=low_stock_threshold,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_INVENTORY_SUMMARY",
        result="SUCCESS",
        user=current_user,
        entity_type="INVENTORY",
        detail_json=result.model_dump(),
        auto_commit=True,
    )
    return result


@router.get("/inventory/movements", response_model=list[InventoryMovementOut])
def list_v5_inventory_movements(
    request: Request,
    warehouse_id: int | None = Query(default=None, gt=0),
    product_id: int | None = Query(default=None, gt=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[InventoryMovementOut]:
    rows = list_inventory_movements(
        db=db,
        warehouse_id=warehouse_id,
        product_id=product_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    result = serialize_inventory_movement_list(db=db, rows=rows)
    write_business_log(
        db=db,
        request=request,
        action="V5_INVENTORY_MOVEMENT_LIST",
        result="SUCCESS",
        user=current_user,
        entity_type="INVENTORY",
        detail_json={"count": len(result)},
        auto_commit=True,
    )
    return result
