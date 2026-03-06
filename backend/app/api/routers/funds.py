from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, require_actor
from app.db.session import get_db
from app.models.payment_doc import PaymentDoc
from app.models.receipt_doc import ReceiptDoc
from app.schemas.funds import (
    PaymentDocResponse,
    PaymentDocSupplementRequest,
    ReceiptDocResponse,
    ReceiptDocSupplementRequest,
)
from app.services.funds_service import (
    FundsServiceError,
    create_payment_doc_supplement,
    create_receipt_doc_supplement,
)

router = APIRouter(tags=["funds"])

fund_doc_write_dependency = require_actor(
    allowed_roles={"finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)


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
    return _to_payment_response(payment_doc, message=result.message)


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
    return _to_receipt_response(receipt_doc, message=result.message)


def _to_payment_response(payment_doc: PaymentDoc, *, message: str) -> PaymentDocResponse:
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
        created_at=payment_doc.created_at,
        message=message,
    )


def _to_receipt_response(receipt_doc: ReceiptDoc, *, message: str) -> ReceiptDocResponse:
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
        created_at=receipt_doc.created_at,
        message=message,
    )
