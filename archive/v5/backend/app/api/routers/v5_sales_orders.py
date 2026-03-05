from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.v5_domain import SalesOrderV5Status
from app.schemas.v5_sales_order import (
    SalesOrderCreateRequest,
    SalesOrderDetailOut,
    SalesOrderFinanceReviewRequest,
    SalesOrderListItemOut,
    SalesOrderOperatorReviewRequest,
    SalesOrderTerminateRequest,
)
from app.schemas.v5_tracking import V5OrderLogOut, V5SalesOrderProgressOut
from app.services.business_log_service import write_business_log
from app.services.v5_sales_order_service import (
    abnormal_close_sales_order,
    apply_finance_review,
    apply_operator_review,
    create_sales_order,
    get_sales_order_with_scope,
    list_sales_orders,
    reject_sales_order,
    serialize_sales_order_detail,
    serialize_sales_order_list,
)
from app.services.v5_tracking_service import build_sales_order_progress, list_sales_order_logs

router = APIRouter(tags=["v5-sales-orders"])


@router.post("/sales-orders", response_model=SalesOrderDetailOut, status_code=status.HTTP_201_CREATED)
def create_v5_sales_order(
    payload: SalesOrderCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.CUSTOMER)),
    db: Session = Depends(get_db),
) -> SalesOrderDetailOut:
    row = create_sales_order(db=db, payload=payload, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_ORDER_CREATE",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_ORDER",
        entity_id=str(row.id),
        detail_json={
            "sales_order_no": row.sales_order_no,
            "warehouse_id": row.warehouse_id,
            "product_id": row.product_id,
            "sales_contract_id": row.sales_contract_id,
        },
    )
    db.commit()
    db.refresh(row)
    return serialize_sales_order_detail(db=db, sales_order=row)


@router.get("/sales-orders", response_model=list[SalesOrderListItemOut])
def list_v5_sales_orders(
    status_value: SalesOrderV5Status | None = Query(default=None, alias="status"),
    pending_only: bool = Query(default=False),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[SalesOrderListItemOut]:
    rows = list_sales_orders(
        db=db,
        current_user=current_user,
        status_value=status_value,
        pending_only=pending_only,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return serialize_sales_order_list(db=db, sales_orders=rows)


@router.get("/sales-orders/{sales_order_id}", response_model=SalesOrderDetailOut)
def get_v5_sales_order(
    sales_order_id: int,
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SalesOrderDetailOut:
    row = get_sales_order_with_scope(db=db, sales_order_id=sales_order_id, current_user=current_user)
    return serialize_sales_order_detail(db=db, sales_order=row)


@router.get("/sales-orders/{sales_order_id}/progress", response_model=V5SalesOrderProgressOut)
def get_v5_sales_order_progress(
    sales_order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> V5SalesOrderProgressOut:
    row = get_sales_order_with_scope(db=db, sales_order_id=sales_order_id, current_user=current_user)
    nodes = build_sales_order_progress(db=db, sales_order=row)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_ORDER_PROGRESS",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_ORDER",
        entity_id=str(row.id),
        detail_json={"count": len(nodes)},
        auto_commit=True,
    )
    return V5SalesOrderProgressOut(order_id=row.id, status=row.status, nodes=nodes)


@router.get("/sales-orders/{sales_order_id}/logs", response_model=list[V5OrderLogOut])
def list_v5_sales_order_logs(
    sales_order_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[V5OrderLogOut]:
    row = get_sales_order_with_scope(db=db, sales_order_id=sales_order_id, current_user=current_user)
    rows = list_sales_order_logs(db=db, sales_order=row)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_ORDER_LOG_LIST",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_ORDER",
        entity_id=str(row.id),
        detail_json={"count": len(rows)},
        auto_commit=True,
    )
    return rows


@router.patch("/sales-orders/{sales_order_id}/operator-review", response_model=SalesOrderDetailOut)
def operator_review_v5_sales_order(
    sales_order_id: int,
    payload: SalesOrderOperatorReviewRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.OPERATOR)),
    db: Session = Depends(get_db),
) -> SalesOrderDetailOut:
    del payload
    row = get_sales_order_with_scope(db=db, sales_order_id=sales_order_id, current_user=current_user)
    row = apply_operator_review(db=db, sales_order=row, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_ORDER_OPERATOR_REVIEW",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_ORDER",
        entity_id=str(row.id),
        before_status=SalesOrderV5Status.SUBMITTED.value,
        after_status=row.status.value,
    )
    db.commit()
    db.refresh(row)
    return serialize_sales_order_detail(db=db, sales_order=row)


@router.patch("/sales-orders/{sales_order_id}/finance-review", response_model=SalesOrderDetailOut)
def finance_review_v5_sales_order(
    sales_order_id: int,
    payload: SalesOrderFinanceReviewRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE)),
    db: Session = Depends(get_db),
) -> SalesOrderDetailOut:
    row = get_sales_order_with_scope(db=db, sales_order_id=sales_order_id, current_user=current_user)
    row, purchase_order, purchase_order_created = apply_finance_review(
        db=db,
        sales_order=row,
        received_amount=payload.received_amount,
        customer_payment_receipt_file_key=payload.customer_payment_receipt_file_key,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_ORDER_FINANCE_REVIEW",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_ORDER",
        entity_id=str(row.id),
        before_status=SalesOrderV5Status.OPERATOR_APPROVED.value,
        after_status=row.status.value,
        detail_json={"purchase_order_id": purchase_order.id},
    )
    if purchase_order_created:
        write_business_log(
            db=db,
            request=request,
            action="V5_PURCHASE_ORDER_CREATE",
            result="SUCCESS",
            user=current_user,
            entity_type="PURCHASE_ORDER",
            entity_id=str(purchase_order.id),
            after_status=purchase_order.status.value,
            detail_json={"sales_order_id": row.id},
        )
    db.commit()
    db.refresh(row)
    return serialize_sales_order_detail(db=db, sales_order=row)


@router.patch("/sales-orders/{sales_order_id}/reject", response_model=SalesOrderDetailOut)
def reject_v5_sales_order(
    sales_order_id: int,
    payload: SalesOrderTerminateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SalesOrderDetailOut:
    row = get_sales_order_with_scope(db=db, sales_order_id=sales_order_id, current_user=current_user)
    before_status = row.status.value
    row = reject_sales_order(
        db=db,
        sales_order=row,
        reason=payload.reason,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_ORDER_REJECT",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_ORDER",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
        reason=payload.reason,
        detail_json={"reason": payload.reason},
    )
    db.commit()
    db.refresh(row)
    return serialize_sales_order_detail(db=db, sales_order=row)


@router.patch("/sales-orders/{sales_order_id}/abnormal-close", response_model=SalesOrderDetailOut)
def abnormal_close_v5_sales_order(
    sales_order_id: int,
    payload: SalesOrderTerminateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SalesOrderDetailOut:
    row = get_sales_order_with_scope(db=db, sales_order_id=sales_order_id, current_user=current_user)
    before_status = row.status.value
    row, purchase_order = abnormal_close_sales_order(
        db=db,
        sales_order=row,
        reason=payload.reason,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_ORDER_ABNORMAL_CLOSE",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_ORDER",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
        reason=payload.reason,
        detail_json={
            "reason": payload.reason,
            "purchase_order_id": purchase_order.id if purchase_order is not None else None,
        },
    )
    db.commit()
    db.refresh(row)
    return serialize_sales_order_detail(db=db, sales_order=row)
