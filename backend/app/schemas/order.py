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
    actual_receipt_amount: Decimal | None = Field(
        default=None, ge=0, description="销售订单实收金额"
    )
    actual_pay_amount: Decimal | None = Field(
        default=None, ge=0, description="采购订单实付金额"
    )
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
    sales_contract_no: str | None = None
    created_at: datetime | None = None


class SalesOrderListItemResponse(BaseModel):
    id: int
    order_no: str
    sales_contract_id: int
    sales_contract_no: str
    oil_product_id: str
    qty_ordered: Decimal
    unit_price: Decimal
    status: str
    submit_comment: str | None = None
    ops_comment: str | None = None
    finance_comment: str | None = None
    purchase_order_id: int | None = None
    submitted_at: datetime | None = None
    created_at: datetime


class SalesOrderListResponse(BaseModel):
    items: list[SalesOrderListItemResponse]
    total: int
    message: str


class AvailableSalesContractItemResponse(BaseModel):
    oil_product_id: str
    qty_signed: Decimal
    unit_price: Decimal


class AvailableSalesContractResponse(BaseModel):
    id: int
    contract_no: str
    customer_id: str
    items: list[AvailableSalesContractItemResponse]


class AvailableSalesContractListResponse(BaseModel):
    items: list[AvailableSalesContractResponse]
    total: int
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
    source_sales_order_no: str | None = None
    supplier_id: str
    oil_product_id: str
    qty_ordered: Decimal
    payable_amount: Decimal
    status: str
    zero_pay_exception_flag: bool
    downstream_tasks: list[SalesOrderDerivativeTaskResponse]
    message: str
    created_at: datetime | None = None


class PurchaseOrderListItemResponse(BaseModel):
    id: int
    order_no: str
    purchase_contract_id: int
    source_sales_order_id: int
    source_sales_order_no: str
    supplier_id: str
    oil_product_id: str
    qty_ordered: Decimal
    payable_amount: Decimal
    status: str
    zero_pay_exception_flag: bool
    created_at: datetime


class PurchaseOrderListResponse(BaseModel):
    items: list[PurchaseOrderListItemResponse]
    total: int
    message: str


class SupplierPurchaseOrderResponse(BaseModel):
    id: int
    order_no: str
    purchase_contract_id: int
    source_sales_order_id: int
    source_sales_order_no: str | None = None
    supplier_id: str
    oil_product_id: str
    qty_ordered: Decimal
    payable_amount: Decimal
    status: str
    zero_pay_exception_flag: bool
    supplier_confirm_comment: str | None = None
    supplier_confirmed_at: datetime | None = None
    payment_validation_status: str | None = None
    payment_validation_hint: str | None = None
    message: str
    created_at: datetime | None = None


class SupplierPurchaseOrderConfirmDeliveryRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=256, description="发货确认说明")


class SupplierPurchaseOrderAttachmentCreateRequest(BaseModel):
    biz_tag: str = Field(description="附件业务标签")
    file_path: str = Field(description="附件路径")


class SupplierPurchaseOrderAttachmentResponse(BaseModel):
    id: int
    owner_doc_type: str
    owner_doc_id: int
    biz_tag: str
    file_path: str
    created_at: datetime
    message: str


class SupplierPurchaseOrderAttachmentListItemResponse(BaseModel):
    id: int
    owner_doc_type: str
    owner_doc_id: int
    biz_tag: str
    file_path: str
    created_at: datetime


class SupplierPurchaseOrderAttachmentListResponse(BaseModel):
    items: list[SupplierPurchaseOrderAttachmentListItemResponse]
    total: int
    message: str
