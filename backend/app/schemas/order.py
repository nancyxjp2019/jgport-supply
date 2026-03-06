from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SalesOrderCreateRequest(BaseModel):
    sales_contract_id: int = Field(gt=0, description="销售合同ID")
    oil_product_id: str = Field(min_length=1, max_length=64, description="油品ID")
    qty: Decimal = Field(gt=0, description="下单数量")
    unit_price: Decimal = Field(gt=0, description="合同单价")


class SalesOrderUpdateRequest(BaseModel):
    oil_product_id: str = Field(min_length=1, max_length=64, description="油品ID")
    qty: Decimal = Field(gt=0, description="下单数量")
    unit_price: Decimal = Field(gt=0, description="合同单价")


class SalesOrderSubmitRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=256, description="提交说明")


class SalesOrderOpsApproveRequest(BaseModel):
    result: bool = Field(description="运营审批结果")
    comment: str = Field(min_length=1, max_length=256, description="运营审批意见")


class SalesOrderFinanceApproveRequest(BaseModel):
    result: bool = Field(description="财务审批结果")
    purchase_contract_id: int | None = Field(default=None, description="采购合同ID")
    actual_receipt_amount: Decimal | None = Field(default=None, ge=0, description="销售订单实收金额")
    actual_pay_amount: Decimal | None = Field(default=None, ge=0, description="采购订单实付金额")
    comment: str = Field(min_length=1, max_length=256, description="财务审批意见")


class SalesOrderResponse(BaseModel):
    id: int
    order_no: str
    sales_contract_id: int
    oil_product_id: str
    qty_ordered: Decimal
    unit_price: Decimal
    status: str
    submit_comment: str | None = None
    ops_comment: str | None = None
    finance_comment: str | None = None
    submitted_at: datetime | None = None
    ops_approved_at: datetime | None = None
    finance_approved_at: datetime | None = None
    purchase_order_id: int | None = None
    generated_task_count: int = 0
    message: str


class SalesOrderDerivativeTaskResponse(BaseModel):
    id: int
    target_doc_type: str
    status: str
    idempotency_key: str


class PurchaseOrderResponse(BaseModel):
    id: int
    order_no: str
    purchase_contract_id: int
    source_sales_order_id: int
    supplier_id: str
    oil_product_id: str
    qty_ordered: Decimal
    payable_amount: Decimal
    status: str
    zero_pay_exception_flag: bool
    downstream_tasks: list[SalesOrderDerivativeTaskResponse]
    message: str
