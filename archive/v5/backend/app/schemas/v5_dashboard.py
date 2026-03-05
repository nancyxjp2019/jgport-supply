from __future__ import annotations

from pydantic import BaseModel

from app.schemas.v5_inventory import InventorySummaryOut


class OverviewContractSummaryOut(BaseModel):
    draft_sales_contract_count: int
    pending_effective_sales_contract_count: int
    active_sales_contract_count: int
    draft_purchase_contract_count: int
    pending_effective_purchase_contract_count: int
    active_purchase_contract_count: int
    pending_sales_qty_ton: float
    pending_purchase_qty_ton: float


class OverviewAmountSummaryOut(BaseModel):
    pending_sales_amount_tax_included: float
    pending_purchase_amount_tax_included: float
    pending_margin_amount_tax_included: float
    received_sales_amount_total: float
    sales_deposit_amount_total: float
    purchase_deposit_amount_total: float
    note: str


class OverviewSalesOrderSummaryOut(BaseModel):
    pending_operator_review_count: int
    pending_finance_review_count: int
    pending_purchase_execution_count: int
    pending_outbound_count: int
    completed_count: int


class OverviewPurchaseOrderSummaryOut(BaseModel):
    pending_submit_or_payment_count: int
    pending_supplier_review_count: int
    pending_warehouse_outbound_count: int
    completed_count: int


class OverviewOrderSummaryOut(BaseModel):
    sales: OverviewSalesOrderSummaryOut
    purchase: OverviewPurchaseOrderSummaryOut
    pending_purchase_stock_in_count: int
    pending_purchase_stock_in_qty_ton: float


class OverviewPendingPurchaseStockInItemOut(BaseModel):
    id: int
    stock_in_no: str
    purchase_contract_no: str
    supplier_company_name: str
    warehouse_name: str
    product_name: str
    stock_in_qty_ton: float


class OverviewSummaryOut(BaseModel):
    contract_summary: OverviewContractSummaryOut
    amount_summary: OverviewAmountSummaryOut
    order_summary: OverviewOrderSummaryOut
    pending_purchase_stock_ins: list[OverviewPendingPurchaseStockInItemOut]
    inventory_summary: InventorySummaryOut
