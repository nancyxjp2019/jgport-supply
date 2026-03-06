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


class PaymentDocConfirmRequest(BaseModel):
    amount_actual: Decimal = Field(ge=0, description="本次确认实付金额")
    voucher_files: list[str] = Field(default_factory=list, description="付款凭证路径列表")


class ReceiptDocConfirmRequest(BaseModel):
    amount_actual: Decimal = Field(ge=0, description="本次确认实收金额")
    voucher_files: list[str] = Field(default_factory=list, description="收款凭证路径列表")


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
    confirmed_at: datetime | None = None
    voucher_file_paths: list[str] = Field(default_factory=list)
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
    confirmed_at: datetime | None = None
    voucher_file_paths: list[str] = Field(default_factory=list)
    created_at: datetime
    message: str
