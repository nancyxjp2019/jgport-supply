from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PaymentDocSupplementRequest(BaseModel):
    contract_id: int = Field(gt=0, description="采购合同ID")
    purchase_order_id: int = Field(gt=0, description="采购订单ID")
    amount_actual: Decimal = Field(gt=0, description="补录付款金额")


class ReceiptDocSupplementRequest(BaseModel):
    contract_id: int = Field(gt=0, description="销售合同ID")
    sales_order_id: int = Field(gt=0, description="销售订单ID")
    amount_actual: Decimal = Field(gt=0, description="补录收款金额")


class ReceiptDocResponse(BaseModel):
    id: int
    doc_no: str
    doc_type: str
    contract_id: int
    sales_order_id: int | None = None
    amount_actual: Decimal
    status: str
    voucher_required: bool
    voucher_exempt_reason: str | None = None
    refund_status: str
    refund_amount: Decimal
    created_at: datetime
    message: str


class PaymentDocResponse(BaseModel):
    id: int
    doc_no: str
    doc_type: str
    contract_id: int
    purchase_order_id: int | None = None
    amount_actual: Decimal
    status: str
    voucher_required: bool
    voucher_exempt_reason: str | None = None
    refund_status: str
    refund_amount: Decimal
    created_at: datetime
    message: str
