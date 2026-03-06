from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.business_audit_log import BusinessAuditLog
from app.models.contract import Contract
from app.models.contract_item import ContractItem
from app.models.purchase_order import PurchaseOrder
from app.models.sales_order import SalesOrder
from app.models.sales_order_derivative_task import SalesOrderDerivativeTask
from app.services.contract_service import (
    CONTRACT_DIRECTION_PURCHASE,
    CONTRACT_DIRECTION_SALES,
    STATUS_EFFECTIVE,
    normalize_price,
    normalize_qty,
)

SALES_ORDER_STATUS_DRAFT = "草稿"
SALES_ORDER_STATUS_PENDING_OPS = "待运营审批"
SALES_ORDER_STATUS_PENDING_FINANCE = "待财务审批"
SALES_ORDER_STATUS_REJECTED = "驳回"
SALES_ORDER_STATUS_DERIVED = "已衍生采购订单"

PURCHASE_ORDER_STATUS_CREATED = "已创建"

MONEY_PRECISION = Decimal("0.01")


@dataclass(frozen=True)
class SalesOrderServiceResult:
    sales_order_id: int
    message: str
    purchase_order_id: int | None = None
    generated_task_count: int = 0


class OrderServiceError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def create_sales_order_draft(
    db: Session,
    *,
    operator_id: str,
    required_customer_company_id: str | None,
    sales_contract_id: int,
    oil_product_id: str,
    qty: Decimal,
    unit_price: Decimal,
) -> SalesOrderServiceResult:
    contract = _get_contract_with_items_or_raise(db, sales_contract_id)
    _validate_sales_contract(contract)
    if required_customer_company_id is not None and contract.customer_id != required_customer_company_id:
        raise OrderServiceError(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前客户无权使用该销售合同创建订单",
        )
    contract_item = _get_contract_item_or_raise(contract.items, oil_product_id)
    normalized_qty = normalize_qty(qty)
    normalized_price = normalize_price(unit_price)
    if normalized_price != contract_item.unit_price:
        raise OrderServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="订单单价必须等于合同单价",
        )

    sales_order = SalesOrder(
        order_no=_generate_doc_no("SO"),
        sales_contract_id=contract.id,
        oil_product_id=oil_product_id,
        qty_ordered=normalized_qty,
        unit_price=normalized_price,
        status=SALES_ORDER_STATUS_DRAFT,
        created_by=operator_id,
        updated_by=operator_id,
    )
    db.add(sales_order)
    db.flush()
    sales_order = get_sales_order_or_raise(db, sales_order.id)
    db.add(
        BusinessAuditLog(
            event_code="M3-SALES-ORDER-CREATE",
            biz_type="sales_order",
            biz_id=f"sales_order:{sales_order.id}",
            operator_id=operator_id,
            before_json={},
            after_json=build_sales_order_snapshot(sales_order),
            extra_json={"sales_contract_id": sales_contract_id},
        )
    )
    _commit_or_raise(db, message="销售订单创建失败，请稍后重试")
    return SalesOrderServiceResult(
        sales_order_id=sales_order.id,
        message="销售订单草稿已创建",
    )


def submit_sales_order(
    db: Session,
    *,
    sales_order_id: int,
    operator_id: str,
    required_customer_company_id: str | None,
    comment: str,
) -> SalesOrderServiceResult:
    sales_order = get_sales_order_or_raise(db, sales_order_id)
    if required_customer_company_id is not None:
        contract = _get_contract_with_items_or_raise(db, sales_order.sales_contract_id)
        if contract.customer_id != required_customer_company_id:
            raise OrderServiceError(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前客户无权提交该销售订单",
            )
    if sales_order.status != SALES_ORDER_STATUS_DRAFT:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前销售订单状态不允许提交审批",
        )

    before_json = build_sales_order_snapshot(sales_order)
    sales_order.status = SALES_ORDER_STATUS_PENDING_OPS
    sales_order.submit_comment = comment
    sales_order.submitted_at = datetime.now(timezone.utc)
    sales_order.updated_by = operator_id
    db.add(
        BusinessAuditLog(
            event_code="M3-SALES-ORDER-SUBMIT",
            biz_type="sales_order",
            biz_id=f"sales_order:{sales_order.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=build_sales_order_snapshot(sales_order),
            extra_json={"comment": comment},
        )
    )
    _commit_or_raise(db, message="销售订单提交审批失败，请稍后重试")
    return SalesOrderServiceResult(
        sales_order_id=sales_order.id,
        message="销售订单已提交运营审批",
    )


def update_sales_order(
    db: Session,
    *,
    sales_order_id: int,
    operator_id: str,
    required_customer_company_id: str | None,
    oil_product_id: str,
    qty: Decimal,
    unit_price: Decimal,
) -> SalesOrderServiceResult:
    sales_order = get_sales_order_or_raise(db, sales_order_id)
    if sales_order.status not in {SALES_ORDER_STATUS_DRAFT, SALES_ORDER_STATUS_REJECTED}:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前销售订单状态不允许修改",
        )

    contract = _get_contract_with_items_or_raise(db, sales_order.sales_contract_id)
    _validate_sales_contract(contract)
    if required_customer_company_id is not None and contract.customer_id != required_customer_company_id:
        raise OrderServiceError(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前客户无权修改该销售订单",
        )

    contract_item = _get_contract_item_or_raise(contract.items, oil_product_id)
    normalized_qty = normalize_qty(qty)
    normalized_price = normalize_price(unit_price)
    if normalized_price != contract_item.unit_price:
        raise OrderServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="订单单价必须等于合同单价",
        )

    before_json = build_sales_order_snapshot(sales_order)
    before_status = sales_order.status
    sales_order.oil_product_id = oil_product_id
    sales_order.qty_ordered = normalized_qty
    sales_order.unit_price = normalized_price
    sales_order.updated_by = operator_id
    if before_status == SALES_ORDER_STATUS_REJECTED:
        sales_order.status = SALES_ORDER_STATUS_DRAFT

    db.add(
        BusinessAuditLog(
            event_code="M3-SALES-ORDER-UPDATE",
            biz_type="sales_order",
            biz_id=f"sales_order:{sales_order.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=build_sales_order_snapshot(sales_order),
            extra_json={"from_status": before_status},
        )
    )
    _commit_or_raise(db, message="销售订单修改失败，请稍后重试")
    if before_status == SALES_ORDER_STATUS_REJECTED:
        message = "销售订单已更新并回到草稿"
    else:
        message = "销售订单草稿已更新"
    return SalesOrderServiceResult(
        sales_order_id=sales_order.id,
        message=message,
    )


def ops_approve_sales_order(
    db: Session,
    *,
    sales_order_id: int,
    operator_id: str,
    result: bool,
    comment: str,
) -> SalesOrderServiceResult:
    sales_order = get_sales_order_or_raise(db, sales_order_id)
    if sales_order.status != SALES_ORDER_STATUS_PENDING_OPS:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前销售订单状态不允许运营审批",
        )

    before_json = build_sales_order_snapshot(sales_order)
    sales_order.ops_comment = comment
    sales_order.ops_approved_by = operator_id
    sales_order.ops_approved_at = datetime.now(timezone.utc)
    sales_order.updated_by = operator_id
    if result:
        sales_order.status = SALES_ORDER_STATUS_PENDING_FINANCE
        event_code = "M3-SALES-ORDER-OPS-APPROVE"
        message = "运营审批通过，已流转财务审批"
    else:
        sales_order.status = SALES_ORDER_STATUS_DRAFT
        event_code = "M3-SALES-ORDER-OPS-REJECT"
        message = "运营审批驳回并退回草稿"

    db.add(
        BusinessAuditLog(
            event_code=event_code,
            biz_type="sales_order",
            biz_id=f"sales_order:{sales_order.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=build_sales_order_snapshot(sales_order),
            extra_json={"comment": comment, "result": result},
        )
    )
    _commit_or_raise(db, message="运营审批处理失败，请稍后重试")
    return SalesOrderServiceResult(
        sales_order_id=sales_order.id,
        message=message,
    )


def finance_approve_sales_order(
    db: Session,
    *,
    sales_order_id: int,
    operator_id: str,
    result: bool,
    purchase_contract_id: int | None,
    actual_receipt_amount: Decimal | None,
    actual_pay_amount: Decimal | None,
    comment: str,
) -> SalesOrderServiceResult:
    sales_order = get_sales_order_or_raise(db, sales_order_id)
    if sales_order.status != SALES_ORDER_STATUS_PENDING_FINANCE:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前销售订单状态不允许财务审批",
        )

    before_json = build_sales_order_snapshot(sales_order)
    sales_order.finance_comment = comment
    sales_order.finance_approved_by = operator_id
    sales_order.finance_approved_at = datetime.now(timezone.utc)
    sales_order.updated_by = operator_id

    if not result:
        sales_order.status = SALES_ORDER_STATUS_REJECTED
        db.add(
            BusinessAuditLog(
                event_code="M3-SALES-ORDER-FINANCE-REJECT",
                biz_type="sales_order",
                biz_id=f"sales_order:{sales_order.id}",
                operator_id=operator_id,
                before_json=before_json,
                after_json=build_sales_order_snapshot(sales_order),
                extra_json={"comment": comment, "result": result},
            )
        )
        _commit_or_raise(db, message="财务审批处理失败，请稍后重试")
        return SalesOrderServiceResult(
            sales_order_id=sales_order.id,
            message="财务审批驳回，订单已进入驳回状态",
        )

    if purchase_contract_id is None or actual_receipt_amount is None or actual_pay_amount is None:
        raise OrderServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="财务审批通过时必须填写采购合同、实收金额和实付金额",
        )

    purchase_contract = _get_contract_with_items_or_raise(db, purchase_contract_id)
    _validate_purchase_contract(purchase_contract)
    purchase_contract_item = _get_contract_item_or_raise(purchase_contract.items, sales_order.oil_product_id)
    _ = purchase_contract_item

    normalized_receipt_amount = normalize_money(actual_receipt_amount)
    normalized_pay_amount = normalize_money(actual_pay_amount)

    purchase_order = PurchaseOrder(
        order_no=_generate_doc_no("PO"),
        purchase_contract_id=purchase_contract.id,
        source_sales_order_id=sales_order.id,
        supplier_id=purchase_contract.supplier_id or "",
        oil_product_id=sales_order.oil_product_id,
        qty_ordered=sales_order.qty_ordered,
        payable_amount=normalized_pay_amount,
        status=PURCHASE_ORDER_STATUS_CREATED,
        zero_pay_exception_flag=normalized_pay_amount == Decimal("0.00"),
        created_by=operator_id,
        updated_by=operator_id,
    )
    if not purchase_order.supplier_id:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="采购合同缺少供应商信息，禁止生成采购订单",
        )
    db.add(purchase_order)
    db.flush()

    tasks = build_sales_order_derivative_tasks(
        sales_order=sales_order,
        purchase_order=purchase_order,
        sales_contract_id=sales_order.sales_contract_id,
        purchase_contract_id=purchase_contract.id,
        actual_receipt_amount=normalized_receipt_amount,
        actual_pay_amount=normalized_pay_amount,
    )
    for task in tasks:
        db.add(task)

    sales_order.status = SALES_ORDER_STATUS_DERIVED
    db.add(
        BusinessAuditLog(
            event_code="M3-PURCHASE-ORDER-CREATE",
            biz_type="purchase_order",
            biz_id=f"purchase_order:{purchase_order.id}",
            operator_id=operator_id,
            before_json={},
            after_json={
                "id": purchase_order.id,
                "order_no": purchase_order.order_no,
                "purchase_contract_id": purchase_order.purchase_contract_id,
                "source_sales_order_id": purchase_order.source_sales_order_id,
                "oil_product_id": purchase_order.oil_product_id,
                "qty_ordered": str(purchase_order.qty_ordered),
                "payable_amount": str(purchase_order.payable_amount),
                "status": purchase_order.status,
                "zero_pay_exception_flag": purchase_order.zero_pay_exception_flag,
            },
            extra_json={
                "generated_from_sales_order_id": sales_order.id,
                "generated_task_count": len(tasks),
            },
        )
    )
    db.add(
        BusinessAuditLog(
            event_code="M3-SALES-ORDER-FINANCE-APPROVE",
            biz_type="sales_order",
            biz_id=f"sales_order:{sales_order.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=build_sales_order_snapshot(sales_order),
            extra_json={
                "comment": comment,
                "result": result,
                "purchase_contract_id": purchase_contract.id,
                "purchase_order_id": purchase_order.id,
                "generated_task_count": len(tasks),
                "zero_pay_exception_flag": purchase_order.zero_pay_exception_flag,
            },
        )
    )
    _commit_or_raise(db, message="财务审批处理失败，请稍后重试")
    return SalesOrderServiceResult(
        sales_order_id=sales_order.id,
        purchase_order_id=purchase_order.id,
        generated_task_count=len(tasks),
        message="财务审批通过，已生成采购订单与收付款任务",
    )


def get_sales_order_or_raise(db: Session, sales_order_id: int) -> SalesOrder:
    statement = (
        select(SalesOrder)
        .options(
            selectinload(SalesOrder.purchase_orders),
            selectinload(SalesOrder.derivative_tasks),
        )
        .where(SalesOrder.id == sales_order_id)
    )
    sales_order = db.scalar(statement)
    if sales_order is None:
        raise OrderServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="销售订单不存在",
        )
    return sales_order


def get_purchase_order_or_raise(db: Session, purchase_order_id: int) -> PurchaseOrder:
    statement = (
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.sales_order).selectinload(SalesOrder.derivative_tasks),
        )
        .where(PurchaseOrder.id == purchase_order_id)
    )
    purchase_order = db.scalar(statement)
    if purchase_order is None:
        raise OrderServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="采购订单不存在",
        )
    return purchase_order


def build_sales_order_snapshot(sales_order: SalesOrder) -> dict:
    return {
        "id": sales_order.id,
        "order_no": sales_order.order_no,
        "sales_contract_id": sales_order.sales_contract_id,
        "oil_product_id": sales_order.oil_product_id,
        "qty_ordered": str(sales_order.qty_ordered),
        "unit_price": str(sales_order.unit_price),
        "status": sales_order.status,
    }


def build_sales_order_derivative_tasks(
    *,
    sales_order: SalesOrder,
    purchase_order: PurchaseOrder,
    sales_contract_id: int,
    purchase_contract_id: int,
    actual_receipt_amount: Decimal,
    actual_pay_amount: Decimal,
) -> list[SalesOrderDerivativeTask]:
    return [
        SalesOrderDerivativeTask(
            sales_order_id=sales_order.id,
            target_doc_type="receipt_doc",
            status="待处理",
            idempotency_key=f"sales_order_finance:{sales_order.id}:receipt_doc",
            payload_json={
                "sales_order_id": sales_order.id,
                "purchase_order_id": purchase_order.id,
                "contract_id": sales_contract_id,
                "amount_actual": str(actual_receipt_amount),
                "zero_amount_flag": actual_receipt_amount == Decimal("0.00"),
                "requires_rule14_validation": actual_receipt_amount == Decimal("0.00"),
            },
        ),
        SalesOrderDerivativeTask(
            sales_order_id=sales_order.id,
            target_doc_type="payment_doc",
            status="待处理",
            idempotency_key=f"sales_order_finance:{sales_order.id}:payment_doc",
            payload_json={
                "sales_order_id": sales_order.id,
                "purchase_order_id": purchase_order.id,
                "contract_id": purchase_contract_id,
                "amount_actual": str(actual_pay_amount),
                "zero_amount_flag": actual_pay_amount == Decimal("0.00"),
                "zero_pay_exception_flag": actual_pay_amount == Decimal("0.00"),
                "requires_rule14_validation": False,
            },
        ),
    ]


def normalize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


def _get_contract_with_items_or_raise(db: Session, contract_id: int) -> Contract:
    statement = (
        select(Contract)
        .options(selectinload(Contract.items))
        .where(Contract.id == contract_id)
    )
    contract = db.scalar(statement)
    if contract is None:
        raise OrderServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联合同不存在",
        )
    return contract


def _get_contract_item_or_raise(items: list[ContractItem], oil_product_id: str) -> ContractItem:
    for item in items:
        if item.oil_product_id == oil_product_id:
            return item
    raise OrderServiceError(
        status_code=status.HTTP_409_CONFLICT,
        detail="合同未包含当前油品明细",
    )


def _validate_sales_contract(contract: Contract) -> None:
    if contract.direction != CONTRACT_DIRECTION_SALES:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前合同不是销售合同，禁止创建销售订单",
        )
    if contract.status != STATUS_EFFECTIVE:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="销售合同未生效，禁止创建销售订单",
        )


def _validate_purchase_contract(contract: Contract) -> None:
    if contract.direction != CONTRACT_DIRECTION_PURCHASE:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前合同不是采购合同，禁止绑定采购订单",
        )
    if contract.status != STATUS_EFFECTIVE:
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="采购合同未生效，禁止生成采购订单",
        )


def _generate_doc_no(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12].upper()}"


def _commit_or_raise(db: Session, *, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise OrderServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="订单编号或上下游关系存在重复",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise OrderServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc
