from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.business_audit_log import BusinessAuditLog
from app.models.contract import Contract
from app.models.contract_effective_task import ContractEffectiveTask
from app.models.contract_item import ContractItem
from app.models.doc_attachment import DocAttachment
from app.models.doc_relation import DocRelation
from app.models.payment_doc import PaymentDoc
from app.models.purchase_order import PurchaseOrder
from app.models.receipt_doc import ReceiptDoc
from app.models.sales_order import SalesOrder
from app.models.sales_order_derivative_task import SalesOrderDerivativeTask
from app.services.contract_close_service import (
    ContractCloseServiceError,
    ensure_contract_open_for_funds,
    evaluate_contract_closure,
)

MONEY_PRECISION = Decimal("0.01")
QTY_PRECISION = Decimal("0.001")

DOC_STATUS_DRAFT = "草稿"
DOC_STATUS_PENDING_SUPPLEMENT = "待补录金额"
DOC_STATUS_CONFIRMED = "已确认"
DOC_STATUS_WRITEOFF = "已核销"
TASK_STATUS_PENDING = "待处理"
TASK_STATUS_GENERATED = "已生成"

DOC_TYPE_DEPOSIT = "DEPOSIT"
DOC_TYPE_NORMAL = "NORMAL"

RELATION_GENERATES = "GENERATES"
RELATION_DERIVES = "DERIVES"
RELATION_BINDS = "BINDS"

ATTACHMENT_BIZ_TAG_RECEIPT_VOUCHER = "RECEIPT_VOUCHER"
ATTACHMENT_BIZ_TAG_PAYMENT_VOUCHER = "PAYMENT_VOUCHER"

RULE11_EXEMPT_REASON = "例外放行（需后补付款单）"
RULE14_EXEMPT_REASON = "保证金覆盖放行（规则14）"


@dataclass(frozen=True)
class FundsServiceResult:
    doc_id: int
    message: str


class FundsServiceError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def materialize_contract_effective_fund_docs(
    db: Session,
    *,
    operator_id: str,
    tasks: list[ContractEffectiveTask],
) -> None:
    for task in tasks:
        if task.target_doc_type not in {"receipt_doc", "payment_doc"} or task.status != TASK_STATUS_PENDING:
            continue

        payload = task.payload_json
        contract_id = int(payload["contract_id"])
        if task.target_doc_type == "receipt_doc":
            receipt_doc = ReceiptDoc(
                doc_no=_generate_doc_no("RCV"),
                doc_type=DOC_TYPE_DEPOSIT,
                contract_id=contract_id,
                sales_order_id=None,
                amount_actual=Decimal("0.00"),
                status=DOC_STATUS_DRAFT,
                voucher_required=True,
                voucher_exempt_reason=None,
                refund_status="未退款",
                refund_amount=Decimal("0.00"),
                created_by=operator_id,
                updated_by=operator_id,
            )
            db.add(receipt_doc)
            db.flush()
            _ensure_doc_relation(
                db,
                source_doc_type="contract",
                source_doc_id=contract_id,
                target_doc_type="receipt_doc",
                target_doc_id=receipt_doc.id,
                relation_type=RELATION_GENERATES,
            )
            _write_fund_audit(
                db,
                event_code="M4-RECEIPT-DOC-GENERATE",
                biz_type="receipt_doc",
                biz_id=f"receipt_doc:{receipt_doc.id}",
                operator_id=operator_id,
                after_json=_build_receipt_snapshot(receipt_doc),
                extra_json={"task_id": task.id, "task_type": "contract_effective"},
            )
        else:
            payment_doc = PaymentDoc(
                doc_no=_generate_doc_no("PAY"),
                doc_type=DOC_TYPE_DEPOSIT,
                contract_id=contract_id,
                purchase_order_id=None,
                amount_actual=Decimal("0.00"),
                status=DOC_STATUS_DRAFT,
                voucher_required=True,
                voucher_exempt_reason=None,
                refund_status="未退款",
                refund_amount=Decimal("0.00"),
                created_by=operator_id,
                updated_by=operator_id,
            )
            db.add(payment_doc)
            db.flush()
            _ensure_doc_relation(
                db,
                source_doc_type="contract",
                source_doc_id=contract_id,
                target_doc_type="payment_doc",
                target_doc_id=payment_doc.id,
                relation_type=RELATION_GENERATES,
            )
            _write_fund_audit(
                db,
                event_code="M4-PAYMENT-DOC-GENERATE",
                biz_type="payment_doc",
                biz_id=f"payment_doc:{payment_doc.id}",
                operator_id=operator_id,
                after_json=_build_payment_snapshot(payment_doc),
                extra_json={"task_id": task.id, "task_type": "contract_effective"},
            )

        task.status = TASK_STATUS_GENERATED


def materialize_sales_order_fund_docs(
    db: Session,
    *,
    operator_id: str,
    tasks: list[SalesOrderDerivativeTask],
) -> None:
    for task in tasks:
        if task.target_doc_type not in {"receipt_doc", "payment_doc"} or task.status != TASK_STATUS_PENDING:
            continue

        payload = task.payload_json
        contract_id = int(payload["contract_id"])
        sales_order_id = int(payload["sales_order_id"])
        amount_actual = normalize_money(Decimal(str(payload["amount_actual"])))

        if task.target_doc_type == "receipt_doc":
            receipt_doc = ReceiptDoc(
                doc_no=_generate_doc_no("RCV"),
                doc_type=DOC_TYPE_NORMAL,
                contract_id=contract_id,
                sales_order_id=sales_order_id,
                amount_actual=amount_actual,
                status=DOC_STATUS_DRAFT,
                voucher_required=True,
                voucher_exempt_reason=None,
                refund_status="未退款",
                refund_amount=Decimal("0.00"),
                created_by=operator_id,
                updated_by=operator_id,
            )
            db.add(receipt_doc)
            db.flush()
            _ensure_doc_relation(
                db,
                source_doc_type="sales_order",
                source_doc_id=sales_order_id,
                target_doc_type="receipt_doc",
                target_doc_id=receipt_doc.id,
                relation_type=RELATION_GENERATES,
            )
            _write_fund_audit(
                db,
                event_code="M4-RECEIPT-DOC-GENERATE",
                biz_type="receipt_doc",
                biz_id=f"receipt_doc:{receipt_doc.id}",
                operator_id=operator_id,
                after_json=_build_receipt_snapshot(receipt_doc),
                extra_json={"task_id": task.id, "task_type": "sales_order_derivative"},
            )
        else:
            purchase_order_id = int(payload["purchase_order_id"])
            zero_pay_exception_flag = bool(payload.get("zero_pay_exception_flag"))
            payment_doc = PaymentDoc(
                doc_no=_generate_doc_no("PAY"),
                doc_type=DOC_TYPE_NORMAL,
                contract_id=contract_id,
                purchase_order_id=purchase_order_id,
                amount_actual=amount_actual,
                status=DOC_STATUS_DRAFT,
                voucher_required=not zero_pay_exception_flag,
                voucher_exempt_reason="例外放行（需后补付款单）" if zero_pay_exception_flag else None,
                refund_status="未退款",
                refund_amount=Decimal("0.00"),
                created_by=operator_id,
                updated_by=operator_id,
            )
            db.add(payment_doc)
            db.flush()
            _ensure_doc_relation(
                db,
                source_doc_type="purchase_order",
                source_doc_id=purchase_order_id,
                target_doc_type="payment_doc",
                target_doc_id=payment_doc.id,
                relation_type=RELATION_GENERATES,
            )
            _write_fund_audit(
                db,
                event_code="M4-PAYMENT-DOC-GENERATE",
                biz_type="payment_doc",
                biz_id=f"payment_doc:{payment_doc.id}",
                operator_id=operator_id,
                after_json=_build_payment_snapshot(payment_doc),
                extra_json={"task_id": task.id, "task_type": "sales_order_derivative"},
            )

        task.status = TASK_STATUS_GENERATED


def create_payment_doc_supplement(
    db: Session,
    *,
    operator_id: str,
    contract_id: int,
    purchase_order_id: int,
    amount_actual: Decimal,
) -> FundsServiceResult:
    contract = _get_contract_or_raise(db, contract_id)
    _ensure_contract_open_for_funds_or_raise(contract)
    purchase_order = _get_purchase_order_or_raise(db, purchase_order_id)
    if purchase_order.purchase_contract_id != contract.id:
        raise FundsServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="采购合同与采购订单不匹配，禁止补录付款单",
        )

    payment_doc = PaymentDoc(
        doc_no=_generate_doc_no("PAY"),
        doc_type=DOC_TYPE_NORMAL,
        contract_id=contract.id,
        purchase_order_id=purchase_order.id,
        amount_actual=normalize_money(amount_actual),
        status=DOC_STATUS_DRAFT,
        voucher_required=True,
        voucher_exempt_reason=None,
        refund_status="未退款",
        refund_amount=Decimal("0.00"),
        created_by=operator_id,
        updated_by=operator_id,
    )
    db.add(payment_doc)
    db.flush()
    _ensure_doc_relation(
        db,
        source_doc_type="contract",
        source_doc_id=contract.id,
        target_doc_type="payment_doc",
        target_doc_id=payment_doc.id,
        relation_type=RELATION_BINDS,
    )
    _ensure_doc_relation(
        db,
        source_doc_type="purchase_order",
        source_doc_id=purchase_order.id,
        target_doc_type="payment_doc",
        target_doc_id=payment_doc.id,
        relation_type=RELATION_BINDS,
    )
    _write_fund_audit(
        db,
        event_code="M4-PAYMENT-DOC-SUPPLEMENT",
        biz_type="payment_doc",
        biz_id=f"payment_doc:{payment_doc.id}",
        operator_id=operator_id,
        after_json=_build_payment_snapshot(payment_doc),
        extra_json={"purchase_order_id": purchase_order.id},
    )
    _commit_or_raise(db, message="补录付款单失败，请稍后重试")
    return FundsServiceResult(doc_id=payment_doc.id, message="付款单草稿已补录")


def create_receipt_doc_supplement(
    db: Session,
    *,
    operator_id: str,
    contract_id: int,
    sales_order_id: int,
    amount_actual: Decimal,
) -> FundsServiceResult:
    contract = _get_contract_or_raise(db, contract_id)
    _ensure_contract_open_for_funds_or_raise(contract)
    sales_order = _get_sales_order_or_raise(db, sales_order_id)
    if sales_order.sales_contract_id != contract.id:
        raise FundsServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="销售合同与销售订单不匹配，禁止补录收款单",
        )

    receipt_doc = ReceiptDoc(
        doc_no=_generate_doc_no("RCV"),
        doc_type=DOC_TYPE_NORMAL,
        contract_id=contract.id,
        sales_order_id=sales_order.id,
        amount_actual=normalize_money(amount_actual),
        status=DOC_STATUS_DRAFT,
        voucher_required=True,
        voucher_exempt_reason=None,
        refund_status="未退款",
        refund_amount=Decimal("0.00"),
        created_by=operator_id,
        updated_by=operator_id,
    )
    db.add(receipt_doc)
    db.flush()
    _ensure_doc_relation(
        db,
        source_doc_type="contract",
        source_doc_id=contract.id,
        target_doc_type="receipt_doc",
        target_doc_id=receipt_doc.id,
        relation_type=RELATION_BINDS,
    )
    _ensure_doc_relation(
        db,
        source_doc_type="sales_order",
        source_doc_id=sales_order.id,
        target_doc_type="receipt_doc",
        target_doc_id=receipt_doc.id,
        relation_type=RELATION_BINDS,
    )
    _write_fund_audit(
        db,
        event_code="M4-RECEIPT-DOC-SUPPLEMENT",
        biz_type="receipt_doc",
        biz_id=f"receipt_doc:{receipt_doc.id}",
        operator_id=operator_id,
        after_json=_build_receipt_snapshot(receipt_doc),
        extra_json={"sales_order_id": sales_order.id},
    )
    _commit_or_raise(db, message="补录收款单失败，请稍后重试")
    return FundsServiceResult(doc_id=receipt_doc.id, message="收款单草稿已补录")


def confirm_payment_doc(
    db: Session,
    *,
    operator_id: str,
    payment_doc_id: int,
    amount_actual: Decimal,
    voucher_files: list[str],
) -> FundsServiceResult:
    payment_doc = _get_payment_doc_or_raise(db, payment_doc_id)
    _ensure_doc_confirmable(payment_doc.status)

    before_json = _build_payment_snapshot(payment_doc)
    normalized_amount = normalize_money(amount_actual)
    normalized_voucher_files = _normalize_voucher_files(voucher_files)
    payment_doc.amount_actual = normalized_amount
    payment_doc.updated_by = operator_id

    if normalized_amount > Decimal("0.00"):
        _ensure_vouchers_present(normalized_voucher_files, detail="非0金额付款单必须上传付款凭证")
        payment_doc.status = DOC_STATUS_CONFIRMED
        payment_doc.voucher_required = True
        payment_doc.voucher_exempt_reason = None
        payment_doc.confirmed_by = operator_id
        payment_doc.confirmed_at = datetime.now(timezone.utc)
        _replace_doc_attachments(
            db,
            owner_doc_type="payment_doc",
            owner_doc_id=payment_doc.id,
            biz_tag=ATTACHMENT_BIZ_TAG_PAYMENT_VOUCHER,
            paths=normalized_voucher_files,
        )
        _write_fund_audit(
            db,
            event_code="M4-PAYMENT-DOC-CONFIRM",
            biz_type="payment_doc",
            biz_id=f"payment_doc:{payment_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_payment_snapshot(payment_doc),
            extra_json={
                "confirm_rule": "NORMAL",
                "voucher_file_count": len(normalized_voucher_files),
            },
        )
        close_result = evaluate_contract_closure(
            db,
            contract_id=payment_doc.contract_id,
            operator_id=operator_id,
            trigger_code="PAYMENT_DOC_CONFIRMED",
        )
        _commit_or_raise(db, message="确认付款单失败，请稍后重试")
        if close_result.closed:
            return FundsServiceResult(doc_id=payment_doc.id, message="付款单已确认，合同已自动关闭")
        return FundsServiceResult(doc_id=payment_doc.id, message="付款单已确认")

    if _is_rule11_zero_pay_doc(db, payment_doc):
        payment_doc.status = DOC_STATUS_CONFIRMED
        payment_doc.voucher_required = False
        payment_doc.voucher_exempt_reason = RULE11_EXEMPT_REASON
        payment_doc.confirmed_by = operator_id
        payment_doc.confirmed_at = datetime.now(timezone.utc)
        _write_fund_audit(
            db,
            event_code="M4-PAYMENT-DOC-CONFIRM",
            biz_type="payment_doc",
            biz_id=f"payment_doc:{payment_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_payment_snapshot(payment_doc),
            extra_json={"confirm_rule": "RULE11", "voucher_file_count": 0},
        )
        close_result = evaluate_contract_closure(
            db,
            contract_id=payment_doc.contract_id,
            operator_id=operator_id,
            trigger_code="PAYMENT_DOC_CONFIRMED",
        )
        _commit_or_raise(db, message="确认付款单失败，请稍后重试")
        if close_result.closed:
            return FundsServiceResult(doc_id=payment_doc.id, message="付款单已按规则11例外确认，合同已自动关闭")
        return FundsServiceResult(doc_id=payment_doc.id, message="付款单已按规则11例外确认")

    if _passes_rule14_for_payment(db, payment_doc):
        payment_doc.status = DOC_STATUS_CONFIRMED
        payment_doc.voucher_required = False
        payment_doc.voucher_exempt_reason = RULE14_EXEMPT_REASON
        payment_doc.confirmed_by = operator_id
        payment_doc.confirmed_at = datetime.now(timezone.utc)
        _write_fund_audit(
            db,
            event_code="M4-PAYMENT-DOC-CONFIRM",
            biz_type="payment_doc",
            biz_id=f"payment_doc:{payment_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_payment_snapshot(payment_doc),
            extra_json={"confirm_rule": "RULE14", "voucher_file_count": 0},
        )
        close_result = evaluate_contract_closure(
            db,
            contract_id=payment_doc.contract_id,
            operator_id=operator_id,
            trigger_code="PAYMENT_DOC_CONFIRMED",
        )
        _commit_or_raise(db, message="确认付款单失败，请稍后重试")
        if close_result.closed:
            return FundsServiceResult(doc_id=payment_doc.id, message="付款单已按规则14免凭证确认，合同已自动关闭")
        return FundsServiceResult(doc_id=payment_doc.id, message="付款单已按规则14免凭证确认")

    payment_doc.status = DOC_STATUS_PENDING_SUPPLEMENT
    payment_doc.voucher_required = True
    payment_doc.voucher_exempt_reason = None
    payment_doc.confirmed_by = None
    payment_doc.confirmed_at = None
    _write_fund_audit(
        db,
        event_code="M4-PAYMENT-DOC-PENDING-SUPPLEMENT",
        biz_type="payment_doc",
        biz_id=f"payment_doc:{payment_doc.id}",
        operator_id=operator_id,
        before_json=before_json,
        after_json=_build_payment_snapshot(payment_doc),
        extra_json={"confirm_rule": "BLOCKED", "blocked_code": "BIZ-PAY-ZERO-001"},
    )
    _commit_or_raise(db, message="确认付款单失败，请稍后重试")
    return FundsServiceResult(doc_id=payment_doc.id, message="0金额付款不满足放行条件，已转待补录金额")


def confirm_receipt_doc(
    db: Session,
    *,
    operator_id: str,
    receipt_doc_id: int,
    amount_actual: Decimal,
    voucher_files: list[str],
) -> FundsServiceResult:
    receipt_doc = _get_receipt_doc_or_raise(db, receipt_doc_id)
    _ensure_doc_confirmable(receipt_doc.status)

    before_json = _build_receipt_snapshot(receipt_doc)
    normalized_amount = normalize_money(amount_actual)
    normalized_voucher_files = _normalize_voucher_files(voucher_files)
    receipt_doc.amount_actual = normalized_amount
    receipt_doc.updated_by = operator_id

    if normalized_amount > Decimal("0.00"):
        _ensure_vouchers_present(normalized_voucher_files, detail="非0金额收款单必须上传收款凭证")
        receipt_doc.status = DOC_STATUS_CONFIRMED
        receipt_doc.voucher_required = True
        receipt_doc.voucher_exempt_reason = None
        receipt_doc.confirmed_by = operator_id
        receipt_doc.confirmed_at = datetime.now(timezone.utc)
        _replace_doc_attachments(
            db,
            owner_doc_type="receipt_doc",
            owner_doc_id=receipt_doc.id,
            biz_tag=ATTACHMENT_BIZ_TAG_RECEIPT_VOUCHER,
            paths=normalized_voucher_files,
        )
        _write_fund_audit(
            db,
            event_code="M4-RECEIPT-DOC-CONFIRM",
            biz_type="receipt_doc",
            biz_id=f"receipt_doc:{receipt_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_receipt_snapshot(receipt_doc),
            extra_json={
                "confirm_rule": "NORMAL",
                "voucher_file_count": len(normalized_voucher_files),
            },
        )
        close_result = evaluate_contract_closure(
            db,
            contract_id=receipt_doc.contract_id,
            operator_id=operator_id,
            trigger_code="RECEIPT_DOC_CONFIRMED",
        )
        _commit_or_raise(db, message="确认收款单失败，请稍后重试")
        if close_result.closed:
            return FundsServiceResult(doc_id=receipt_doc.id, message="收款单已确认，合同已自动关闭")
        return FundsServiceResult(doc_id=receipt_doc.id, message="收款单已确认")

    if _passes_rule14_for_receipt(db, receipt_doc):
        receipt_doc.status = DOC_STATUS_CONFIRMED
        receipt_doc.voucher_required = False
        receipt_doc.voucher_exempt_reason = RULE14_EXEMPT_REASON
        receipt_doc.confirmed_by = operator_id
        receipt_doc.confirmed_at = datetime.now(timezone.utc)
        _write_fund_audit(
            db,
            event_code="M4-RECEIPT-DOC-CONFIRM",
            biz_type="receipt_doc",
            biz_id=f"receipt_doc:{receipt_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_receipt_snapshot(receipt_doc),
            extra_json={"confirm_rule": "RULE14", "voucher_file_count": 0},
        )
        close_result = evaluate_contract_closure(
            db,
            contract_id=receipt_doc.contract_id,
            operator_id=operator_id,
            trigger_code="RECEIPT_DOC_CONFIRMED",
        )
        _commit_or_raise(db, message="确认收款单失败，请稍后重试")
        if close_result.closed:
            return FundsServiceResult(doc_id=receipt_doc.id, message="收款单已按规则14免凭证确认，合同已自动关闭")
        return FundsServiceResult(doc_id=receipt_doc.id, message="收款单已按规则14免凭证确认")

    receipt_doc.status = DOC_STATUS_PENDING_SUPPLEMENT
    receipt_doc.voucher_required = True
    receipt_doc.voucher_exempt_reason = None
    receipt_doc.confirmed_by = None
    receipt_doc.confirmed_at = None
    _write_fund_audit(
        db,
        event_code="M4-RECEIPT-DOC-PENDING-SUPPLEMENT",
        biz_type="receipt_doc",
        biz_id=f"receipt_doc:{receipt_doc.id}",
        operator_id=operator_id,
        before_json=before_json,
        after_json=_build_receipt_snapshot(receipt_doc),
        extra_json={"confirm_rule": "BLOCKED", "blocked_code": "BIZ-RECEIPT-ZERO-001"},
    )
    _commit_or_raise(db, message="确认收款单失败，请稍后重试")
    return FundsServiceResult(doc_id=receipt_doc.id, message="0金额收款不满足放行条件，已转待补录金额")


def normalize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


def normalize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_PRECISION)


def ensure_sales_purchase_relation(
    db: Session,
    *,
    sales_order_id: int,
    purchase_order_id: int,
) -> None:
    _ensure_doc_relation(
        db,
        source_doc_type="sales_order",
        source_doc_id=sales_order_id,
        target_doc_type="purchase_order",
        target_doc_id=purchase_order_id,
        relation_type=RELATION_DERIVES,
    )


def _ensure_doc_relation(
    db: Session,
    *,
    source_doc_type: str,
    source_doc_id: int,
    target_doc_type: str,
    target_doc_id: int,
    relation_type: str,
) -> None:
    statement = select(DocRelation.id).where(
        DocRelation.source_doc_type == source_doc_type,
        DocRelation.source_doc_id == source_doc_id,
        DocRelation.target_doc_type == target_doc_type,
        DocRelation.target_doc_id == target_doc_id,
        DocRelation.relation_type == relation_type,
    )
    if db.scalar(statement) is not None:
        return
    db.add(
        DocRelation(
            source_doc_type=source_doc_type,
            source_doc_id=source_doc_id,
            target_doc_type=target_doc_type,
            target_doc_id=target_doc_id,
            relation_type=relation_type,
        )
    )


def _get_contract_or_raise(db: Session, contract_id: int) -> Contract:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise FundsServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联合同不存在",
        )
    return contract


def _ensure_contract_open_for_funds_or_raise(contract: Contract) -> None:
    try:
        ensure_contract_open_for_funds(contract)
    except ContractCloseServiceError as exc:
        raise FundsServiceError(status_code=exc.status_code, detail=exc.detail) from exc


def _get_contract_item_or_raise(db: Session, contract_id: int, oil_product_id: str) -> ContractItem:
    statement = select(ContractItem).where(
        ContractItem.contract_id == contract_id,
        ContractItem.oil_product_id == oil_product_id,
    )
    contract_item = db.scalar(statement)
    if contract_item is None:
        raise FundsServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="关联合同缺少当前油品明细",
        )
    return contract_item


def _get_purchase_order_or_raise(db: Session, purchase_order_id: int) -> PurchaseOrder:
    purchase_order = db.get(PurchaseOrder, purchase_order_id)
    if purchase_order is None:
        raise FundsServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="采购订单不存在",
        )
    return purchase_order


def _get_sales_order_or_raise(db: Session, sales_order_id: int) -> SalesOrder:
    sales_order = db.get(SalesOrder, sales_order_id)
    if sales_order is None:
        raise FundsServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="销售订单不存在",
        )
    return sales_order


def _get_payment_doc_or_raise(db: Session, payment_doc_id: int) -> PaymentDoc:
    payment_doc = db.get(PaymentDoc, payment_doc_id)
    if payment_doc is None:
        raise FundsServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="付款单不存在",
        )
    return payment_doc


def _get_receipt_doc_or_raise(db: Session, receipt_doc_id: int) -> ReceiptDoc:
    receipt_doc = db.get(ReceiptDoc, receipt_doc_id)
    if receipt_doc is None:
        raise FundsServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收款单不存在",
        )
    return receipt_doc


def _ensure_doc_confirmable(status_value: str) -> None:
    if status_value not in {DOC_STATUS_DRAFT, DOC_STATUS_PENDING_SUPPLEMENT}:
        raise FundsServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前资金单据状态不允许确认",
        )


def _ensure_vouchers_present(voucher_files: list[str], *, detail: str) -> None:
    if not voucher_files:
        raise FundsServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )


def _normalize_voucher_files(voucher_files: list[str]) -> list[str]:
    normalized_files: list[str] = []
    seen_paths: set[str] = set()
    for path in voucher_files:
        normalized_path = path.strip()
        if not normalized_path:
            raise FundsServiceError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="凭证路径不能为空",
            )
        if len(normalized_path) > 512:
            raise FundsServiceError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="凭证路径长度不能超过512个字符",
            )
        if normalized_path in seen_paths:
            continue
        normalized_files.append(normalized_path)
        seen_paths.add(normalized_path)
    return normalized_files


def _replace_doc_attachments(
    db: Session,
    *,
    owner_doc_type: str,
    owner_doc_id: int,
    biz_tag: str,
    paths: list[str],
) -> None:
    statement = select(DocAttachment).where(
        DocAttachment.owner_doc_type == owner_doc_type,
        DocAttachment.owner_doc_id == owner_doc_id,
        DocAttachment.biz_tag == biz_tag,
    )
    for attachment in db.scalars(statement).all():
        db.delete(attachment)
    for path in paths:
        db.add(
            DocAttachment(
                owner_doc_type=owner_doc_type,
                owner_doc_id=owner_doc_id,
                path=path,
                biz_tag=biz_tag,
            )
        )


def list_doc_attachment_paths(
    db: Session,
    *,
    owner_doc_type: str,
    owner_doc_id: int,
    biz_tag: str,
) -> list[str]:
    statement = (
        select(DocAttachment.path)
        .where(
            DocAttachment.owner_doc_type == owner_doc_type,
            DocAttachment.owner_doc_id == owner_doc_id,
            DocAttachment.biz_tag == biz_tag,
        )
        .order_by(DocAttachment.id)
    )
    return list(db.scalars(statement).all())


def _is_rule11_zero_pay_doc(db: Session, payment_doc: PaymentDoc) -> bool:
    if payment_doc.doc_type != DOC_TYPE_NORMAL or payment_doc.purchase_order_id is None:
        return False
    purchase_order = _get_purchase_order_or_raise(db, payment_doc.purchase_order_id)
    return purchase_order.zero_pay_exception_flag is True


def _passes_rule14_for_receipt(db: Session, receipt_doc: ReceiptDoc) -> bool:
    if receipt_doc.doc_type != DOC_TYPE_NORMAL or receipt_doc.sales_order_id is None:
        return False
    sales_order = _get_sales_order_or_raise(db, receipt_doc.sales_order_id)
    contract_item = _get_contract_item_or_raise(db, receipt_doc.contract_id, sales_order.oil_product_id)
    release_threshold = _get_release_threshold_or_raise(db, receipt_doc.contract_id)
    deposit_cover_qty = _calculate_sales_deposit_cover_qty(
        db,
        contract_id=receipt_doc.contract_id,
        unit_price=contract_item.unit_price,
    )
    pending_qty = normalize_qty(contract_item.qty_signed - contract_item.qty_out_acc)
    allowed_qty = normalize_qty(deposit_cover_qty * release_threshold)
    return pending_qty <= allowed_qty


def _passes_rule14_for_payment(db: Session, payment_doc: PaymentDoc) -> bool:
    if payment_doc.doc_type != DOC_TYPE_NORMAL or payment_doc.purchase_order_id is None:
        return False
    purchase_order = _get_purchase_order_or_raise(db, payment_doc.purchase_order_id)
    contract_item = _get_contract_item_or_raise(db, payment_doc.contract_id, purchase_order.oil_product_id)
    release_threshold = _get_release_threshold_or_raise(db, payment_doc.contract_id)
    deposit_cover_qty = _calculate_purchase_deposit_cover_qty(
        db,
        contract_id=payment_doc.contract_id,
        unit_price=contract_item.unit_price,
    )
    pending_qty = normalize_qty(contract_item.qty_signed - contract_item.qty_in_acc)
    allowed_qty = normalize_qty(deposit_cover_qty * release_threshold)
    return pending_qty <= allowed_qty


def _get_release_threshold_or_raise(db: Session, contract_id: int) -> Decimal:
    contract = _get_contract_or_raise(db, contract_id)
    if contract.threshold_release_snapshot is None:
        raise FundsServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同缺少阈值快照，禁止执行零金额放行校验",
        )
    return Decimal(str(contract.threshold_release_snapshot))


def _calculate_sales_deposit_cover_qty(
    db: Session,
    *,
    contract_id: int,
    unit_price: Decimal,
) -> Decimal:
    deposit_net_amount = Decimal("0.00")
    statement = select(ReceiptDoc).where(
        ReceiptDoc.contract_id == contract_id,
        ReceiptDoc.doc_type == DOC_TYPE_DEPOSIT,
        ReceiptDoc.status.in_([DOC_STATUS_CONFIRMED, DOC_STATUS_WRITEOFF]),
    )
    for receipt_doc in db.scalars(statement).all():
        if receipt_doc.refund_status == "已退款":
            continue
        deposit_net_amount += normalize_money(receipt_doc.amount_actual - receipt_doc.refund_amount)
    if unit_price <= Decimal("0.00"):
        raise FundsServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同单价异常，无法计算保证金覆盖数量",
        )
    return normalize_qty(deposit_net_amount / unit_price)


def _calculate_purchase_deposit_cover_qty(
    db: Session,
    *,
    contract_id: int,
    unit_price: Decimal,
) -> Decimal:
    deposit_net_amount = Decimal("0.00")
    statement = select(PaymentDoc).where(
        PaymentDoc.contract_id == contract_id,
        PaymentDoc.doc_type == DOC_TYPE_DEPOSIT,
        PaymentDoc.status.in_([DOC_STATUS_CONFIRMED, DOC_STATUS_WRITEOFF]),
    )
    for payment_doc in db.scalars(statement).all():
        if payment_doc.refund_status == "已退款":
            continue
        deposit_net_amount += normalize_money(payment_doc.amount_actual - payment_doc.refund_amount)
    if unit_price <= Decimal("0.00"):
        raise FundsServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同单价异常，无法计算保证金覆盖数量",
        )
    return normalize_qty(deposit_net_amount / unit_price)


def _write_fund_audit(
    db: Session,
    *,
    event_code: str,
    biz_type: str,
    biz_id: str,
    operator_id: str,
    before_json: dict | None = None,
    after_json: dict,
    extra_json: dict,
) -> None:
    db.add(
        BusinessAuditLog(
            event_code=event_code,
            biz_type=biz_type,
            biz_id=biz_id,
            operator_id=operator_id,
            before_json=before_json or {},
            after_json=after_json,
            extra_json=extra_json,
        )
    )


def _build_receipt_snapshot(receipt_doc: ReceiptDoc) -> dict:
    return {
        "id": receipt_doc.id,
        "doc_no": receipt_doc.doc_no,
        "doc_type": receipt_doc.doc_type,
        "contract_id": receipt_doc.contract_id,
        "sales_order_id": receipt_doc.sales_order_id,
        "amount_actual": str(receipt_doc.amount_actual),
        "status": receipt_doc.status,
        "voucher_required": receipt_doc.voucher_required,
        "voucher_exempt_reason": receipt_doc.voucher_exempt_reason,
        "refund_status": receipt_doc.refund_status,
        "refund_amount": str(receipt_doc.refund_amount),
        "confirmed_by": receipt_doc.confirmed_by,
        "confirmed_at": receipt_doc.confirmed_at.isoformat() if receipt_doc.confirmed_at else None,
    }


def _build_payment_snapshot(payment_doc: PaymentDoc) -> dict:
    return {
        "id": payment_doc.id,
        "doc_no": payment_doc.doc_no,
        "doc_type": payment_doc.doc_type,
        "contract_id": payment_doc.contract_id,
        "purchase_order_id": payment_doc.purchase_order_id,
        "amount_actual": str(payment_doc.amount_actual),
        "status": payment_doc.status,
        "voucher_required": payment_doc.voucher_required,
        "voucher_exempt_reason": payment_doc.voucher_exempt_reason,
        "refund_status": payment_doc.refund_status,
        "refund_amount": str(payment_doc.refund_amount),
        "confirmed_by": payment_doc.confirmed_by,
        "confirmed_at": payment_doc.confirmed_at.isoformat() if payment_doc.confirmed_at else None,
    }


def _generate_doc_no(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12].upper()}"


def _commit_or_raise(db: Session, *, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise FundsServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="资金单据编号或上下游关系存在重复",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise FundsServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc
