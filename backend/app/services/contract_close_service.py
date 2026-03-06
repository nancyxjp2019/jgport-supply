from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.business_audit_log import BusinessAuditLog
from app.models.contract import Contract
from app.models.inbound_doc import InboundDoc
from app.models.outbound_doc import OutboundDoc
from app.models.payment_doc import PaymentDoc
from app.models.receipt_doc import ReceiptDoc

MONEY_PRECISION = Decimal("0.01")
QTY_PRECISION = Decimal("0.001")

CONTRACT_STATUS_EFFECTIVE = "生效中"
CONTRACT_STATUS_QTY_DONE = "数量履约完成"
CONTRACT_STATUS_CLOSED = "已关闭"
CONTRACT_STATUS_MANUAL_CLOSED = "手工关闭"
CONTRACT_STATUS_ARCHIVED = "已归档"

CLOSE_TYPE_AUTO = "AUTO"
CLOSE_TYPE_MANUAL = "MANUAL"

DOC_STATUS_DRAFT = "草稿"
DOC_STATUS_PENDING_SUPPLEMENT = "待补录金额"
DOC_STATUS_PENDING_SUBMIT = "待提交"
DOC_STATUS_VALIDATION_FAILED = "校验失败"
DOC_STATUS_CONFIRMED = "已确认"
DOC_STATUS_WRITEOFF = "已核销"
DOC_STATUS_TERMINATED = "已终止"

MANUAL_CLOSE_CONFIRM_TOKEN = "MANUAL_CLOSE"


@dataclass(frozen=True)
class ContractCloseResult:
    contract_id: int
    message: str
    closed: bool


class ContractCloseServiceError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def evaluate_contract_closure(
    db: Session,
    *,
    contract_id: int,
    operator_id: str,
    trigger_code: str,
) -> ContractCloseResult:
    contract = _get_contract_with_close_relations_or_raise(db, contract_id)
    if contract.status in {CONTRACT_STATUS_CLOSED, CONTRACT_STATUS_MANUAL_CLOSED, CONTRACT_STATUS_ARCHIVED}:
        return ContractCloseResult(contract_id=contract.id, message="合同已关闭，无需重复校验", closed=False)
    if contract.status != CONTRACT_STATUS_QTY_DONE and not _contract_qty_done(contract):
        return ContractCloseResult(contract_id=contract.id, message="合同尚未达到关闭条件", closed=False)

    expected_amount = _calculate_expected_amount(contract)
    actual_amount = _calculate_net_amount(contract)
    amount_gap = normalize_money(expected_amount - actual_amount)
    if abs(amount_gap) > MONEY_PRECISION:
        return ContractCloseResult(contract_id=contract.id, message="合同金额闭环未满足，暂不自动关闭", closed=False)

    before_json = _build_contract_snapshot(contract)
    terminated_summary = _terminate_open_docs(
        db,
        contract=contract,
        operator_id=operator_id,
        reason="合同自动关闭收口",
        reason_code="AUTO_CLOSE",
    )
    contract.status = CONTRACT_STATUS_CLOSED
    contract.close_type = CLOSE_TYPE_AUTO
    contract.closed_by = operator_id
    contract.closed_at = datetime.now(timezone.utc)
    contract.updated_by = operator_id
    _write_contract_close_audit(
        db,
        event_code="M6-CONTRACT-AUTO-CLOSE",
        contract=contract,
        operator_id=operator_id,
        before_json=before_json,
        expected_amount=expected_amount,
        actual_amount=actual_amount,
        amount_gap=amount_gap,
        terminated_summary=terminated_summary,
        extra_json={"trigger_code": trigger_code},
    )
    return ContractCloseResult(contract_id=contract.id, message="合同已自动关闭", closed=True)


def manual_close_contract(
    db: Session,
    *,
    contract_id: int,
    operator_id: str,
    reason: str,
    confirm_token: str,
) -> ContractCloseResult:
    normalized_token = confirm_token.strip().upper()
    if normalized_token != MANUAL_CLOSE_CONFIRM_TOKEN:
        raise ContractCloseServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="手工关闭确认口令不正确",
        )

    contract = _get_contract_with_close_relations_or_raise(db, contract_id)
    if contract.status in {CONTRACT_STATUS_CLOSED, CONTRACT_STATUS_MANUAL_CLOSED, CONTRACT_STATUS_ARCHIVED}:
        raise ContractCloseServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前合同状态不允许手工关闭",
        )
    if not _contract_qty_done(contract):
        raise ContractCloseServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同未达到数量履约完成，禁止手工关闭",
        )

    expected_amount = _calculate_expected_amount(contract)
    actual_amount = _calculate_net_amount(contract)
    amount_gap = normalize_money(expected_amount - actual_amount)
    diff_qty_json = _build_manual_close_diff_qty_json(contract)
    before_json = _build_contract_snapshot(contract)
    terminated_summary = _terminate_open_docs(
        db,
        contract=contract,
        operator_id=operator_id,
        reason="合同手工关闭收口",
        reason_code="MANUAL_CLOSE",
    )
    now = datetime.now(timezone.utc)
    contract.status = CONTRACT_STATUS_MANUAL_CLOSED
    contract.close_type = CLOSE_TYPE_MANUAL
    contract.manual_close_reason = reason.strip()
    contract.manual_close_by = operator_id
    contract.manual_close_at = now
    contract.manual_close_diff_amount = amount_gap
    contract.manual_close_diff_qty_json = diff_qty_json
    contract.closed_by = operator_id
    contract.closed_at = now
    contract.updated_by = operator_id
    _write_contract_close_audit(
        db,
        event_code="M6-CONTRACT-MANUAL-CLOSE",
        contract=contract,
        operator_id=operator_id,
        before_json=before_json,
        expected_amount=expected_amount,
        actual_amount=actual_amount,
        amount_gap=amount_gap,
        terminated_summary=terminated_summary,
        extra_json={
            "reason": reason.strip(),
            "confirm_token": MANUAL_CLOSE_CONFIRM_TOKEN,
            "manual_close_diff_qty_json": diff_qty_json,
        },
    )
    _commit_or_raise(db, message="手工关闭合同失败，请稍后重试")
    return ContractCloseResult(contract_id=contract.id, message="合同已手工关闭", closed=True)


def normalize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


def normalize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_PRECISION)


def ensure_contract_open_for_funds(contract: Contract) -> None:
    if contract.status in {CONTRACT_STATUS_EFFECTIVE, CONTRACT_STATUS_QTY_DONE}:
        return
    raise ContractCloseServiceError(
        status_code=status.HTTP_409_CONFLICT,
        detail="合同已关闭，禁止继续补录或确认资金单据",
    )


def _get_contract_with_close_relations_or_raise(db: Session, contract_id: int) -> Contract:
    statement = (
        select(Contract)
        .options(
            selectinload(Contract.items),
            selectinload(Contract.receipt_docs),
            selectinload(Contract.payment_docs),
            selectinload(Contract.inbound_docs),
            selectinload(Contract.outbound_docs),
        )
        .where(Contract.id == contract_id)
    )
    contract = db.scalar(statement)
    if contract is None:
        raise ContractCloseServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合同不存在",
        )
    return contract


def _contract_qty_done(contract: Contract) -> bool:
    if contract.direction == "purchase":
        return all(item.qty_in_acc >= item.qty_signed for item in contract.items)
    return all(item.qty_out_acc >= item.qty_signed for item in contract.items)


def _calculate_expected_amount(contract: Contract) -> Decimal:
    total_amount = Decimal("0.00")
    for item in contract.items:
        qty_value = item.qty_in_acc if contract.direction == "purchase" else item.qty_out_acc
        total_amount += normalize_money(Decimal(str(qty_value)) * Decimal(str(item.unit_price)))
    return normalize_money(total_amount)


def _calculate_net_amount(contract: Contract) -> Decimal:
    total_amount = Decimal("0.00")
    if contract.direction == "purchase":
        for payment_doc in contract.payment_docs:
            if payment_doc.status not in {DOC_STATUS_CONFIRMED, DOC_STATUS_WRITEOFF}:
                continue
            if payment_doc.refund_status == "已退款":
                continue
            total_amount += normalize_money(payment_doc.amount_actual - payment_doc.refund_amount)
    else:
        for receipt_doc in contract.receipt_docs:
            if receipt_doc.status not in {DOC_STATUS_CONFIRMED, DOC_STATUS_WRITEOFF}:
                continue
            if receipt_doc.refund_status == "已退款":
                continue
            total_amount += normalize_money(receipt_doc.amount_actual - receipt_doc.refund_amount)
    return normalize_money(total_amount)


def _build_manual_close_diff_qty_json(contract: Contract) -> list[dict[str, str]]:
    diff_items: list[dict[str, str]] = []
    for item in contract.items:
        qty_done = item.qty_in_acc if contract.direction == "purchase" else item.qty_out_acc
        diff_items.append(
            {
                "oil_product_id": item.oil_product_id,
                "qty_signed": str(item.qty_signed),
                "qty_done": str(qty_done),
                "diff_qty": str(normalize_qty(item.qty_signed - qty_done)),
            }
        )
    return diff_items


def _terminate_open_docs(
    db: Session,
    *,
    contract: Contract,
    operator_id: str,
    reason: str,
    reason_code: str,
) -> dict[str, list[int]]:
    terminated_summary = {
        "receipt_doc_ids": [],
        "payment_doc_ids": [],
        "inbound_doc_ids": [],
        "outbound_doc_ids": [],
    }

    for receipt_doc in contract.receipt_docs:
        if receipt_doc.status not in {DOC_STATUS_DRAFT, DOC_STATUS_PENDING_SUPPLEMENT}:
            continue
        before_json = _build_receipt_snapshot(receipt_doc)
        receipt_doc.status = DOC_STATUS_TERMINATED
        receipt_doc.updated_by = operator_id
        terminated_summary["receipt_doc_ids"].append(receipt_doc.id)
        _write_doc_terminate_audit(
            db,
            event_code="M6-RECEIPT-DOC-TERMINATE",
            biz_type="receipt_doc",
            biz_id=f"receipt_doc:{receipt_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_receipt_snapshot(receipt_doc),
            reason=reason,
            reason_code=reason_code,
        )

    for payment_doc in contract.payment_docs:
        if payment_doc.status not in {DOC_STATUS_DRAFT, DOC_STATUS_PENDING_SUPPLEMENT}:
            continue
        before_json = _build_payment_snapshot(payment_doc)
        payment_doc.status = DOC_STATUS_TERMINATED
        payment_doc.updated_by = operator_id
        terminated_summary["payment_doc_ids"].append(payment_doc.id)
        _write_doc_terminate_audit(
            db,
            event_code="M6-PAYMENT-DOC-TERMINATE",
            biz_type="payment_doc",
            biz_id=f"payment_doc:{payment_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_payment_snapshot(payment_doc),
            reason=reason,
            reason_code=reason_code,
        )

    for inbound_doc in contract.inbound_docs:
        if inbound_doc.status not in {DOC_STATUS_DRAFT, DOC_STATUS_PENDING_SUBMIT, DOC_STATUS_VALIDATION_FAILED}:
            continue
        before_json = _build_inbound_snapshot(inbound_doc)
        inbound_doc.status = DOC_STATUS_TERMINATED
        inbound_doc.updated_by = operator_id
        terminated_summary["inbound_doc_ids"].append(inbound_doc.id)
        _write_doc_terminate_audit(
            db,
            event_code="M6-INBOUND-DOC-TERMINATE",
            biz_type="inbound_doc",
            biz_id=f"inbound_doc:{inbound_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_inbound_snapshot(inbound_doc),
            reason=reason,
            reason_code=reason_code,
        )

    for outbound_doc in contract.outbound_docs:
        if outbound_doc.status not in {DOC_STATUS_DRAFT, DOC_STATUS_PENDING_SUBMIT, DOC_STATUS_VALIDATION_FAILED}:
            continue
        before_json = _build_outbound_snapshot(outbound_doc)
        outbound_doc.status = DOC_STATUS_TERMINATED
        outbound_doc.updated_by = operator_id
        terminated_summary["outbound_doc_ids"].append(outbound_doc.id)
        _write_doc_terminate_audit(
            db,
            event_code="M6-OUTBOUND-DOC-TERMINATE",
            biz_type="outbound_doc",
            biz_id=f"outbound_doc:{outbound_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_outbound_snapshot(outbound_doc),
            reason=reason,
            reason_code=reason_code,
        )

    return terminated_summary


def _write_contract_close_audit(
    db: Session,
    *,
    event_code: str,
    contract: Contract,
    operator_id: str,
    before_json: dict,
    expected_amount: Decimal,
    actual_amount: Decimal,
    amount_gap: Decimal,
    terminated_summary: dict[str, list[int]],
    extra_json: dict,
) -> None:
    payload = {
        "expected_amount": str(expected_amount),
        "actual_amount": str(actual_amount),
        "amount_gap": str(amount_gap),
        "terminated_summary": terminated_summary,
    }
    payload.update(extra_json)
    db.add(
        BusinessAuditLog(
            event_code=event_code,
            biz_type="contract",
            biz_id=f"contract:{contract.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_contract_snapshot(contract),
            extra_json=payload,
        )
    )


def _write_doc_terminate_audit(
    db: Session,
    *,
    event_code: str,
    biz_type: str,
    biz_id: str,
    operator_id: str,
    before_json: dict,
    after_json: dict,
    reason: str,
    reason_code: str,
) -> None:
    db.add(
        BusinessAuditLog(
            event_code=event_code,
            biz_type=biz_type,
            biz_id=biz_id,
            operator_id=operator_id,
            before_json=before_json,
            after_json=after_json,
            extra_json={"reason": reason, "reason_code": reason_code},
        )
    )


def _build_contract_snapshot(contract: Contract) -> dict:
    return {
        "id": contract.id,
        "contract_no": contract.contract_no,
        "direction": contract.direction,
        "status": contract.status,
        "close_type": contract.close_type,
        "closed_by": contract.closed_by,
        "closed_at": contract.closed_at.isoformat() if contract.closed_at else None,
        "manual_close_reason": contract.manual_close_reason,
        "manual_close_by": contract.manual_close_by,
        "manual_close_at": contract.manual_close_at.isoformat() if contract.manual_close_at else None,
        "manual_close_diff_amount": str(contract.manual_close_diff_amount) if contract.manual_close_diff_amount is not None else None,
        "manual_close_diff_qty_json": contract.manual_close_diff_qty_json,
        "items": [
            {
                "id": item.id,
                "oil_product_id": item.oil_product_id,
                "qty_signed": str(item.qty_signed),
                "qty_in_acc": str(item.qty_in_acc),
                "qty_out_acc": str(item.qty_out_acc),
                "unit_price": str(item.unit_price),
            }
            for item in contract.items
        ],
    }


def _build_receipt_snapshot(receipt_doc: ReceiptDoc) -> dict:
    return {
        "id": receipt_doc.id,
        "doc_no": receipt_doc.doc_no,
        "contract_id": receipt_doc.contract_id,
        "sales_order_id": receipt_doc.sales_order_id,
        "doc_type": receipt_doc.doc_type,
        "amount_actual": str(receipt_doc.amount_actual),
        "status": receipt_doc.status,
        "refund_status": receipt_doc.refund_status,
        "refund_amount": str(receipt_doc.refund_amount),
    }


def _build_payment_snapshot(payment_doc: PaymentDoc) -> dict:
    return {
        "id": payment_doc.id,
        "doc_no": payment_doc.doc_no,
        "contract_id": payment_doc.contract_id,
        "purchase_order_id": payment_doc.purchase_order_id,
        "doc_type": payment_doc.doc_type,
        "amount_actual": str(payment_doc.amount_actual),
        "status": payment_doc.status,
        "refund_status": payment_doc.refund_status,
        "refund_amount": str(payment_doc.refund_amount),
    }


def _build_inbound_snapshot(inbound_doc: InboundDoc) -> dict:
    return {
        "id": inbound_doc.id,
        "doc_no": inbound_doc.doc_no,
        "contract_id": inbound_doc.contract_id,
        "purchase_order_id": inbound_doc.purchase_order_id,
        "oil_product_id": inbound_doc.oil_product_id,
        "warehouse_id": inbound_doc.warehouse_id,
        "source_type": inbound_doc.source_type,
        "actual_qty": str(inbound_doc.actual_qty),
        "status": inbound_doc.status,
    }


def _build_outbound_snapshot(outbound_doc: OutboundDoc) -> dict:
    return {
        "id": outbound_doc.id,
        "doc_no": outbound_doc.doc_no,
        "contract_id": outbound_doc.contract_id,
        "sales_order_id": outbound_doc.sales_order_id,
        "oil_product_id": outbound_doc.oil_product_id,
        "warehouse_id": outbound_doc.warehouse_id,
        "source_type": outbound_doc.source_type,
        "source_ticket_no": outbound_doc.source_ticket_no,
        "manual_ref_no": outbound_doc.manual_ref_no,
        "actual_qty": str(outbound_doc.actual_qty),
        "status": outbound_doc.status,
    }


def _commit_or_raise(db: Session, *, message: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise ContractCloseServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc
