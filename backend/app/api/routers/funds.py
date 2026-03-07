from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, require_actor
from app.db.session import get_db
from app.models.payment_doc import PaymentDoc
from app.models.receipt_doc import ReceiptDoc
from app.schemas.funds import (
    PaymentDocConfirmRequest,
    PaymentDocListItem,
    PaymentDocListResponse,
    PaymentDocResponse,
    PaymentDocSupplementRequest,
    ReceiptDocConfirmRequest,
    ReceiptDocListItem,
    ReceiptDocListResponse,
    ReceiptDocResponse,
    ReceiptDocSupplementRequest,
)
from app.services.funds_service import (
    FundsServiceError,
    ATTACHMENT_BIZ_TAG_PAYMENT_VOUCHER,
    ATTACHMENT_BIZ_TAG_RECEIPT_VOUCHER,
    confirm_payment_doc,
    confirm_receipt_doc,
    create_payment_doc_supplement,
    create_receipt_doc_supplement,
    list_doc_attachment_paths,
)

router = APIRouter(tags=["funds"])

fund_doc_write_dependency = require_actor(
    allowed_roles={"finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)
fund_doc_read_dependency = require_actor(
    allowed_roles={"finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)


@router.get("/payment-docs", response_model=PaymentDocListResponse)
def list_payment_docs(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    _: AuthenticatedActor = Depends(fund_doc_read_dependency),
    db: Session = Depends(get_db),
) -> PaymentDocListResponse:
    statement = select(PaymentDoc).order_by(
        PaymentDoc.created_at.desc(), PaymentDoc.id.desc()
    )
    normalized_status = status_filter.strip() if status_filter else ""
    if normalized_status:
        statement = statement.where(PaymentDoc.status == normalized_status)
    payment_docs = list(db.scalars(statement.limit(limit)).all())
    return PaymentDocListResponse(
        items=[_to_payment_list_item(doc) for doc in payment_docs],
        total=len(payment_docs),
        message="付款单列表查询成功",
    )


@router.get("/receipt-docs", response_model=ReceiptDocListResponse)
def list_receipt_docs(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    _: AuthenticatedActor = Depends(fund_doc_read_dependency),
    db: Session = Depends(get_db),
) -> ReceiptDocListResponse:
    statement = select(ReceiptDoc).order_by(
        ReceiptDoc.created_at.desc(), ReceiptDoc.id.desc()
    )
    normalized_status = status_filter.strip() if status_filter else ""
    if normalized_status:
        statement = statement.where(ReceiptDoc.status == normalized_status)
    receipt_docs = list(db.scalars(statement.limit(limit)).all())
    return ReceiptDocListResponse(
        items=[_to_receipt_list_item(doc) for doc in receipt_docs],
        total=len(receipt_docs),
        message="收款单列表查询成功",
    )


@router.get("/payment-docs/{payment_doc_id}", response_model=PaymentDocResponse)
def get_payment_doc_detail(
    payment_doc_id: int,
    _: AuthenticatedActor = Depends(fund_doc_read_dependency),
    db: Session = Depends(get_db),
) -> PaymentDocResponse:
    payment_doc = db.get(PaymentDoc, payment_doc_id)
    if payment_doc is None:
        raise HTTPException(status_code=404, detail="付款单不存在")
    return _to_payment_response(payment_doc, message="付款单详情查询成功", db=db)


@router.get("/receipt-docs/{receipt_doc_id}", response_model=ReceiptDocResponse)
def get_receipt_doc_detail(
    receipt_doc_id: int,
    _: AuthenticatedActor = Depends(fund_doc_read_dependency),
    db: Session = Depends(get_db),
) -> ReceiptDocResponse:
    receipt_doc = db.get(ReceiptDoc, receipt_doc_id)
    if receipt_doc is None:
        raise HTTPException(status_code=404, detail="收款单不存在")
    return _to_receipt_response(receipt_doc, message="收款单详情查询成功", db=db)


@router.post("/payment-docs/supplement", response_model=PaymentDocResponse)
def create_payment_supplement(
    payload: PaymentDocSupplementRequest,
    actor: AuthenticatedActor = Depends(fund_doc_write_dependency),
    db: Session = Depends(get_db),
) -> PaymentDocResponse:
    try:
        result = create_payment_doc_supplement(
            db,
            operator_id=actor.user_id,
            contract_id=payload.contract_id,
            purchase_order_id=payload.purchase_order_id,
            amount_actual=payload.amount_actual,
        )
        payment_doc = db.get(PaymentDoc, result.doc_id)
    except FundsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert payment_doc is not None
    return _to_payment_response(payment_doc, message=result.message, db=db)


@router.post("/receipt-docs/supplement", response_model=ReceiptDocResponse)
def create_receipt_supplement(
    payload: ReceiptDocSupplementRequest,
    actor: AuthenticatedActor = Depends(fund_doc_write_dependency),
    db: Session = Depends(get_db),
) -> ReceiptDocResponse:
    try:
        result = create_receipt_doc_supplement(
            db,
            operator_id=actor.user_id,
            contract_id=payload.contract_id,
            sales_order_id=payload.sales_order_id,
            amount_actual=payload.amount_actual,
        )
        receipt_doc = db.get(ReceiptDoc, result.doc_id)
    except FundsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert receipt_doc is not None
    return _to_receipt_response(receipt_doc, message=result.message, db=db)


@router.post(
    "/payment-docs/{payment_doc_id}/confirm", response_model=PaymentDocResponse
)
def confirm_payment(
    payment_doc_id: int,
    payload: PaymentDocConfirmRequest,
    actor: AuthenticatedActor = Depends(fund_doc_write_dependency),
    db: Session = Depends(get_db),
) -> PaymentDocResponse:
    try:
        result = confirm_payment_doc(
            db,
            operator_id=actor.user_id,
            payment_doc_id=payment_doc_id,
            amount_actual=payload.amount_actual,
            voucher_files=payload.voucher_files,
        )
        payment_doc = db.get(PaymentDoc, result.doc_id)
    except FundsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert payment_doc is not None
    return _to_payment_response(payment_doc, message=result.message, db=db)


@router.post(
    "/receipt-docs/{receipt_doc_id}/confirm", response_model=ReceiptDocResponse
)
def confirm_receipt(
    receipt_doc_id: int,
    payload: ReceiptDocConfirmRequest,
    actor: AuthenticatedActor = Depends(fund_doc_write_dependency),
    db: Session = Depends(get_db),
) -> ReceiptDocResponse:
    try:
        result = confirm_receipt_doc(
            db,
            operator_id=actor.user_id,
            receipt_doc_id=receipt_doc_id,
            amount_actual=payload.amount_actual,
            voucher_files=payload.voucher_files,
        )
        receipt_doc = db.get(ReceiptDoc, result.doc_id)
    except FundsServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert receipt_doc is not None
    return _to_receipt_response(receipt_doc, message=result.message, db=db)


def _to_payment_response(
    payment_doc: PaymentDoc, *, message: str, db: Session
) -> PaymentDocResponse:
    return PaymentDocResponse(
        id=payment_doc.id,
        doc_no=payment_doc.doc_no,
        doc_type=payment_doc.doc_type,
        contract_id=payment_doc.contract_id,
        purchase_order_id=payment_doc.purchase_order_id,
        amount_actual=payment_doc.amount_actual,
        status=payment_doc.status,
        voucher_required=payment_doc.voucher_required,
        voucher_exempt_reason=payment_doc.voucher_exempt_reason,
        refund_status=payment_doc.refund_status,
        refund_amount=payment_doc.refund_amount,
        confirmed_at=payment_doc.confirmed_at,
        voucher_file_paths=list_doc_attachment_paths(
            db,
            owner_doc_type="payment_doc",
            owner_doc_id=payment_doc.id,
            biz_tag=ATTACHMENT_BIZ_TAG_PAYMENT_VOUCHER,
        ),
        created_at=payment_doc.created_at,
        message=message,
    )


def _to_payment_list_item(payment_doc: PaymentDoc) -> PaymentDocListItem:
    return PaymentDocListItem(
        id=payment_doc.id,
        doc_no=payment_doc.doc_no,
        doc_type=payment_doc.doc_type,
        contract_id=payment_doc.contract_id,
        purchase_order_id=payment_doc.purchase_order_id,
        amount_actual=payment_doc.amount_actual,
        status=payment_doc.status,
        voucher_required=payment_doc.voucher_required,
        voucher_exempt_reason=payment_doc.voucher_exempt_reason,
        refund_status=payment_doc.refund_status,
        refund_amount=payment_doc.refund_amount,
        confirmed_at=payment_doc.confirmed_at,
        created_at=payment_doc.created_at,
    )


def _to_receipt_response(
    receipt_doc: ReceiptDoc, *, message: str, db: Session
) -> ReceiptDocResponse:
    return ReceiptDocResponse(
        id=receipt_doc.id,
        doc_no=receipt_doc.doc_no,
        doc_type=receipt_doc.doc_type,
        contract_id=receipt_doc.contract_id,
        sales_order_id=receipt_doc.sales_order_id,
        amount_actual=receipt_doc.amount_actual,
        status=receipt_doc.status,
        voucher_required=receipt_doc.voucher_required,
        voucher_exempt_reason=receipt_doc.voucher_exempt_reason,
        refund_status=receipt_doc.refund_status,
        refund_amount=receipt_doc.refund_amount,
        confirmed_at=receipt_doc.confirmed_at,
        voucher_file_paths=list_doc_attachment_paths(
            db,
            owner_doc_type="receipt_doc",
            owner_doc_id=receipt_doc.id,
            biz_tag=ATTACHMENT_BIZ_TAG_RECEIPT_VOUCHER,
        ),
        created_at=receipt_doc.created_at,
        message=message,
    )


def _to_receipt_list_item(receipt_doc: ReceiptDoc) -> ReceiptDocListItem:
    return ReceiptDocListItem(
        id=receipt_doc.id,
        doc_no=receipt_doc.doc_no,
        doc_type=receipt_doc.doc_type,
        contract_id=receipt_doc.contract_id,
        sales_order_id=receipt_doc.sales_order_id,
        amount_actual=receipt_doc.amount_actual,
        status=receipt_doc.status,
        voucher_required=receipt_doc.voucher_required,
        voucher_exempt_reason=receipt_doc.voucher_exempt_reason,
        refund_status=receipt_doc.refund_status,
        refund_amount=receipt_doc.refund_amount,
        confirmed_at=receipt_doc.confirmed_at,
        created_at=receipt_doc.created_at,
    )
