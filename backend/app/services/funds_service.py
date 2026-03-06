from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.business_audit_log import BusinessAuditLog
from app.models.contract import Contract
from app.models.contract_effective_task import ContractEffectiveTask
from app.models.doc_relation import DocRelation
from app.models.payment_doc import PaymentDoc
from app.models.purchase_order import PurchaseOrder
from app.models.receipt_doc import ReceiptDoc
from app.models.sales_order import SalesOrder
from app.models.sales_order_derivative_task import SalesOrderDerivativeTask

MONEY_PRECISION = Decimal("0.01")

DOC_STATUS_DRAFT = "草稿"
TASK_STATUS_PENDING = "待处理"
TASK_STATUS_GENERATED = "已生成"

DOC_TYPE_DEPOSIT = "DEPOSIT"
DOC_TYPE_NORMAL = "NORMAL"

RELATION_GENERATES = "GENERATES"
RELATION_DERIVES = "DERIVES"
RELATION_BINDS = "BINDS"


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


def normalize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


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


def _write_fund_audit(
    db: Session,
    *,
    event_code: str,
    biz_type: str,
    biz_id: str,
    operator_id: str,
    after_json: dict,
    extra_json: dict,
) -> None:
    db.add(
        BusinessAuditLog(
            event_code=event_code,
            biz_type=biz_type,
            biz_id=biz_id,
            operator_id=operator_id,
            before_json={},
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
