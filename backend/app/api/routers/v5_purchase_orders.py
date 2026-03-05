from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.v5_domain import PurchaseOrderV5Status
from app.schemas.v5_purchase_order import (
    PurchaseOrderAbnormalCloseRequest,
    PurchaseOrderDetailOut,
    PurchaseOrderListItemOut,
    PurchaseOrderSubmitRequest,
    PurchaseOrderSupplierReviewRequest,
    PurchaseOrderWarehouseOutboundRequest,
)
from app.schemas.v5_tracking import V5OrderLogOut
from app.services.business_log_service import write_business_log
from app.services.v5_purchase_order_service import (
    abnormal_close_purchase_order,
    apply_supplier_review,
    apply_warehouse_outbound,
    get_purchase_order_with_scope,
    list_purchase_orders,
    serialize_purchase_order_detail,
    serialize_purchase_order_list,
    submit_purchase_order,
)
from app.services.v5_tracking_service import list_purchase_order_logs

router = APIRouter(tags=["v5-purchase-orders"])


@router.get("/purchase-orders", response_model=list[PurchaseOrderListItemOut])
def list_v5_purchase_orders(
    status_value: PurchaseOrderV5Status | None = Query(default=None, alias="status"),
    pending_only: bool = Query(default=False),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.SUPPLIER, UserRole.WAREHOUSE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[PurchaseOrderListItemOut]:
    rows = list_purchase_orders(
        db=db,
        current_user=current_user,
        status_value=status_value,
        pending_only=pending_only,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return serialize_purchase_order_list(db=db, purchase_orders=rows, current_user=current_user)


@router.get("/purchase-orders/{purchase_order_id}", response_model=PurchaseOrderDetailOut)
def get_v5_purchase_order(
    purchase_order_id: int,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.SUPPLIER, UserRole.WAREHOUSE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseOrderDetailOut:
    row = get_purchase_order_with_scope(db=db, purchase_order_id=purchase_order_id, current_user=current_user)
    return serialize_purchase_order_detail(db=db, purchase_order=row, current_user=current_user)


@router.get("/purchase-orders/{purchase_order_id}/logs", response_model=list[V5OrderLogOut])
def list_v5_purchase_order_logs(
    purchase_order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[V5OrderLogOut]:
    row = get_purchase_order_with_scope(db=db, purchase_order_id=purchase_order_id, current_user=current_user)
    rows = list_purchase_order_logs(db=db, purchase_order=row)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_ORDER_LOG_LIST",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_ORDER",
        entity_id=str(row.id),
        detail_json={"count": len(rows)},
        auto_commit=True,
    )
    return rows


@router.patch("/purchase-orders/{purchase_order_id}/submit", response_model=PurchaseOrderDetailOut)
def submit_v5_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderSubmitRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE)),
    db: Session = Depends(get_db),
) -> PurchaseOrderDetailOut:
    row = get_purchase_order_with_scope(db=db, purchase_order_id=purchase_order_id, current_user=current_user)
    row = submit_purchase_order(
        db=db,
        purchase_order=row,
        purchase_contract_id=payload.purchase_contract_id,
        delivery_instruction_template_id=payload.delivery_instruction_template_id,
        confirm_snapshot=payload.confirm_snapshot,
        confirm_acknowledged=payload.confirm_acknowledged,
        supplier_payment_voucher_file_keys=payload.supplier_payment_voucher_file_keys,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_ORDER_SUBMIT",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_ORDER",
        entity_id=str(row.id),
        before_status=PurchaseOrderV5Status.PENDING_SUBMIT.value,
        after_status=row.status.value,
    )
    db.commit()
    db.refresh(row)
    return serialize_purchase_order_detail(db=db, purchase_order=row, current_user=current_user)



@router.patch("/purchase-orders/{purchase_order_id}/supplier-review", response_model=PurchaseOrderDetailOut)
def supplier_review_v5_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderSupplierReviewRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.SUPPLIER)),
    db: Session = Depends(get_db),
) -> PurchaseOrderDetailOut:
    row = get_purchase_order_with_scope(db=db, purchase_order_id=purchase_order_id, current_user=current_user)
    row, sales_order = apply_supplier_review(
        db=db,
        purchase_order=row,
        supplier_delivery_doc_file_key=payload.supplier_delivery_doc_file_key,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_ORDER_SUPPLIER_REVIEW",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_ORDER",
        entity_id=str(row.id),
        before_status=PurchaseOrderV5Status.SUPPLIER_REVIEW_PENDING.value,
        after_status=row.status.value,
        detail_json={"sales_order_status": sales_order.status.value},
    )
    db.commit()
    db.refresh(row)
    return serialize_purchase_order_detail(db=db, purchase_order=row, current_user=current_user)


@router.patch("/purchase-orders/{purchase_order_id}/warehouse-outbound", response_model=PurchaseOrderDetailOut)
def warehouse_outbound_v5_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderWarehouseOutboundRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.WAREHOUSE)),
    db: Session = Depends(get_db),
) -> PurchaseOrderDetailOut:
    row = get_purchase_order_with_scope(db=db, purchase_order_id=purchase_order_id, current_user=current_user)
    row, sales_order = apply_warehouse_outbound(
        db=db,
        purchase_order=row,
        actual_outbound_qty=payload.actual_outbound_qty,
        outbound_doc_file_key=payload.outbound_doc_file_key,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_ORDER_WAREHOUSE_OUTBOUND",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_ORDER",
        entity_id=str(row.id),
        before_status=PurchaseOrderV5Status.WAREHOUSE_PENDING.value,
        after_status=row.status.value,
        detail_json={"sales_order_status": sales_order.status.value},
    )
    db.commit()
    db.refresh(row)
    return serialize_purchase_order_detail(db=db, purchase_order=row, current_user=current_user)


@router.patch("/purchase-orders/{purchase_order_id}/abnormal-close", response_model=PurchaseOrderDetailOut)
def abnormal_close_v5_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderAbnormalCloseRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseOrderDetailOut:
    row = get_purchase_order_with_scope(db=db, purchase_order_id=purchase_order_id, current_user=current_user)
    before_status = row.status.value
    row, sales_order = abnormal_close_purchase_order(
        db=db,
        purchase_order=row,
        reason=payload.reason,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_ORDER_ABNORMAL_CLOSE",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_ORDER",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
        reason=payload.reason,
        detail_json={
            "reason": payload.reason,
            "sales_order_status": sales_order.status.value,
        },
    )
    db.commit()
    db.refresh(row)
    return serialize_purchase_order_detail(db=db, purchase_order=row, current_user=current_user)
