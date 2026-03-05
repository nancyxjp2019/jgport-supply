from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.v5_domain import (
    ContractStatus,
    PurchaseContract,
    PurchaseContractItem,
    PurchaseOrderV5,
    PurchaseOrderV5Status,
    PurchaseStockInStatus,
    SalesContract,
    SalesContractItem,
    SalesOrderV5,
    SalesOrderV5Status,
)
from app.schemas.v5_dashboard import (
    OverviewAmountSummaryOut,
    OverviewContractSummaryOut,
    OverviewOrderSummaryOut,
    OverviewPendingPurchaseStockInItemOut,
    OverviewPurchaseOrderSummaryOut,
    OverviewSalesOrderSummaryOut,
    OverviewSummaryOut,
)
from app.services.v5_inventory_service import (
    list_purchase_stock_ins,
    serialize_purchase_stock_in_list,
    summarize_inventory,
)


ACTIVE_CONTRACT_STATUSES = (ContractStatus.EFFECTIVE, ContractStatus.PARTIALLY_EXECUTED)
DEPOSIT_TRACKING_CONTRACT_STATUSES = (ContractStatus.PENDING_EFFECTIVE, ContractStatus.EFFECTIVE, ContractStatus.PARTIALLY_EXECUTED)
OVERVIEW_AMOUNT_NOTE = (
    "待执行金额按合同当前待执行数量占合同总量比例折算；已收款按销售订单已录入收款金额累计；"
    "保证金按待生效及执行中合同统计，仅供经营看板参考，不作为对账结算依据。"
)


def _count_rows(db: Session, model, *conditions) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


def _sum_decimal(db: Session, column, *conditions, precision: str = "0.01") -> Decimal:
    value = db.scalar(select(func.coalesce(func.sum(column), Decimal("0.00"))).where(*conditions))
    return Decimal(str(value or 0)).quantize(Decimal(precision))


def _build_pending_contract_metrics(
    db: Session,
    *,
    contract_model,
    item_model,
    contract_item_fk: str,
    pending_qty_field: str,
) -> tuple[int, Decimal, Decimal]:
    pending_column = getattr(contract_model, pending_qty_field)
    contracts = db.scalars(
        select(contract_model).where(
            contract_model.status.in_(ACTIVE_CONTRACT_STATUSES),
            pending_column > Decimal("0.0000"),
        )
    ).all()
    if not contracts:
        return 0, Decimal("0.0000"), Decimal("0.00")

    contract_ids = [item.id for item in contracts]
    fk_column = getattr(item_model, contract_item_fk)
    amount_rows = db.execute(
        select(fk_column, func.coalesce(func.sum(item_model.amount_tax_included), Decimal("0.00")))
        .where(fk_column.in_(contract_ids))
        .group_by(fk_column)
    ).all()
    amount_map = {int(contract_id): Decimal(str(amount or 0)) for contract_id, amount in amount_rows}

    pending_qty_total = Decimal("0.0000")
    pending_amount_total = Decimal("0.00")
    for contract in contracts:
        pending_qty = Decimal(str(getattr(contract, pending_qty_field) or 0)).quantize(Decimal("0.0000"))
        effective_qty = Decimal(str(contract.effective_contract_qty or 0)).quantize(Decimal("0.0000"))
        pending_qty_total = (pending_qty_total + pending_qty).quantize(Decimal("0.0000"))
        if effective_qty <= 0:
            continue
        ratio = pending_qty / effective_qty
        if ratio < 0:
            ratio = Decimal("0")
        if ratio > 1:
            ratio = Decimal("1")
        pending_amount_total = (pending_amount_total + (amount_map.get(contract.id, Decimal("0.00")) * ratio)).quantize(
            Decimal("0.01")
        )
    return len(contracts), pending_qty_total, pending_amount_total


def build_overview_summary(
    db: Session,
    *,
    current_user: User,
    low_stock_threshold: float,
) -> OverviewSummaryOut:
    sales_active_count, pending_sales_qty, pending_sales_amount = _build_pending_contract_metrics(
        db,
        contract_model=SalesContract,
        item_model=SalesContractItem,
        contract_item_fk="sales_contract_id",
        pending_qty_field="pending_execution_qty",
    )
    purchase_active_count, pending_purchase_qty, pending_purchase_amount = _build_pending_contract_metrics(
        db,
        contract_model=PurchaseContract,
        item_model=PurchaseContractItem,
        contract_item_fk="purchase_contract_id",
        pending_qty_field="pending_execution_qty",
    )

    pending_stock_ins = list_purchase_stock_ins(
        db=db,
        status_value=PurchaseStockInStatus.PENDING_CONFIRM,
        page=1,
        page_size=20,
    )
    pending_stock_in_rows = serialize_purchase_stock_in_list(db=db, rows=pending_stock_ins)
    pending_stock_in_qty = Decimal("0.0000")
    for row in pending_stock_in_rows:
        pending_stock_in_qty = (pending_stock_in_qty + Decimal(str(row.stock_in_qty_ton or 0))).quantize(Decimal("0.0000"))

    inventory_summary = summarize_inventory(
        db=db,
        current_user=current_user,
        low_stock_threshold=low_stock_threshold,
    )

    received_sales_amount_total = _sum_decimal(
        db,
        SalesOrderV5.received_amount,
        SalesOrderV5.received_amount.is_not(None),
        SalesOrderV5.status != SalesOrderV5Status.REJECTED,
    )
    sales_deposit_amount_total = _sum_decimal(
        db,
        SalesContract.deposit_amount,
        SalesContract.status.in_(DEPOSIT_TRACKING_CONTRACT_STATUSES),
    )
    purchase_deposit_amount_total = _sum_decimal(
        db,
        PurchaseContract.deposit_amount,
        PurchaseContract.status.in_(DEPOSIT_TRACKING_CONTRACT_STATUSES),
    )

    return OverviewSummaryOut(
        contract_summary=OverviewContractSummaryOut(
            draft_sales_contract_count=_count_rows(db, SalesContract, SalesContract.status == ContractStatus.DRAFT),
            pending_effective_sales_contract_count=_count_rows(
                db,
                SalesContract,
                SalesContract.status == ContractStatus.PENDING_EFFECTIVE,
            ),
            active_sales_contract_count=sales_active_count,
            draft_purchase_contract_count=_count_rows(db, PurchaseContract, PurchaseContract.status == ContractStatus.DRAFT),
            pending_effective_purchase_contract_count=_count_rows(
                db,
                PurchaseContract,
                PurchaseContract.status == ContractStatus.PENDING_EFFECTIVE,
            ),
            active_purchase_contract_count=purchase_active_count,
            pending_sales_qty_ton=float(pending_sales_qty),
            pending_purchase_qty_ton=float(pending_purchase_qty),
        ),
        amount_summary=OverviewAmountSummaryOut(
            pending_sales_amount_tax_included=float(pending_sales_amount),
            pending_purchase_amount_tax_included=float(pending_purchase_amount),
            pending_margin_amount_tax_included=float((pending_sales_amount - pending_purchase_amount).quantize(Decimal("0.01"))),
            received_sales_amount_total=float(received_sales_amount_total),
            sales_deposit_amount_total=float(sales_deposit_amount_total),
            purchase_deposit_amount_total=float(purchase_deposit_amount_total),
            note=OVERVIEW_AMOUNT_NOTE,
        ),
        order_summary=OverviewOrderSummaryOut(
            sales=OverviewSalesOrderSummaryOut(
                pending_operator_review_count=_count_rows(db, SalesOrderV5, SalesOrderV5.status == SalesOrderV5Status.SUBMITTED),
                pending_finance_review_count=_count_rows(
                    db,
                    SalesOrderV5,
                    SalesOrderV5.status == SalesOrderV5Status.OPERATOR_APPROVED,
                ),
                pending_purchase_execution_count=_count_rows(
                    db,
                    SalesOrderV5,
                    SalesOrderV5.status == SalesOrderV5Status.CUSTOMER_PAYMENT_CONFIRMED,
                ),
                pending_outbound_count=_count_rows(
                    db,
                    SalesOrderV5,
                    SalesOrderV5.status == SalesOrderV5Status.READY_FOR_OUTBOUND,
                ),
                completed_count=_count_rows(db, SalesOrderV5, SalesOrderV5.status == SalesOrderV5Status.COMPLETED),
            ),
            purchase=OverviewPurchaseOrderSummaryOut(
                pending_submit_or_payment_count=_count_rows(
                    db,
                    PurchaseOrderV5,
                    PurchaseOrderV5.status.in_(
                        (
                            PurchaseOrderV5Status.PENDING_SUBMIT,
                            PurchaseOrderV5Status.SUPPLIER_PAYMENT_PENDING,
                        )
                    ),
                ),
                pending_supplier_review_count=_count_rows(
                    db,
                    PurchaseOrderV5,
                    PurchaseOrderV5.status == PurchaseOrderV5Status.SUPPLIER_REVIEW_PENDING,
                ),
                pending_warehouse_outbound_count=_count_rows(
                    db,
                    PurchaseOrderV5,
                    PurchaseOrderV5.status == PurchaseOrderV5Status.WAREHOUSE_PENDING,
                ),
                completed_count=_count_rows(
                    db,
                    PurchaseOrderV5,
                    PurchaseOrderV5.status == PurchaseOrderV5Status.COMPLETED,
                ),
            ),
            pending_purchase_stock_in_count=len(pending_stock_in_rows),
            pending_purchase_stock_in_qty_ton=float(pending_stock_in_qty),
        ),
        pending_purchase_stock_ins=[
            OverviewPendingPurchaseStockInItemOut(
                id=row.id,
                stock_in_no=row.stock_in_no,
                purchase_contract_no=row.purchase_contract_no,
                supplier_company_name=row.supplier_company_name,
                warehouse_name=row.warehouse_name,
                product_name=row.product_name,
                stock_in_qty_ton=row.stock_in_qty_ton,
            )
            for row in pending_stock_in_rows
        ],
        inventory_summary=inventory_summary,
    )
