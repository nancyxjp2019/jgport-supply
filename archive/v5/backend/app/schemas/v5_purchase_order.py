from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.v5_domain import PurchaseOrderV5Status


class PurchaseOrderSubmitRequest(BaseModel):
    purchase_contract_id: int = Field(gt=0)
    delivery_instruction_template_id: int = Field(gt=0)
    confirm_snapshot: dict[str, object]
    confirm_acknowledged: bool
    # BR-078：财务提交采购订单时必须同步上传向供应商付款凭证，支持多个附件（至少1个，最多9个）
    supplier_payment_voucher_file_keys: list[str] = Field(min_length=1, max_length=9)

    @field_validator("supplier_payment_voucher_file_keys", mode="before")
    @classmethod
    def normalize_payment_file_keys(cls, value: object) -> list[str]:
        # 兼容前端传单个字符串的情况
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise ValueError("付款凭证文件键必须为列表")
        normalized = [str(item or "").strip().strip("/") for item in value]
        if not all(normalized):
            raise ValueError("付款凭证文件键不能为空")
        return normalized

    @model_validator(mode="after")
    def validate_confirm_acknowledged(self) -> "PurchaseOrderSubmitRequest":
        if not self.confirm_acknowledged:
            raise ValueError("采购订单提交前必须完成二次确认")
        return self


class PurchaseOrderSupplierPaymentRequest(BaseModel):
    supplier_payment_voucher_file_key: str = Field(min_length=1, max_length=255)

    @field_validator("supplier_payment_voucher_file_key", mode="before")
    @classmethod
    def normalize_file_key(cls, value: str) -> str:
        return str(value or "").strip().strip("/")


class PurchaseOrderSupplierReviewRequest(BaseModel):
    supplier_delivery_doc_file_key: str = Field(min_length=1, max_length=255)

    @field_validator("supplier_delivery_doc_file_key", mode="before")
    @classmethod
    def normalize_file_key(cls, value: str) -> str:
        return str(value or "").strip().strip("/")


class PurchaseOrderWarehouseOutboundRequest(BaseModel):
    actual_outbound_qty: float = Field(gt=0)
    outbound_doc_file_key: str = Field(min_length=1, max_length=255)

    @field_validator("outbound_doc_file_key", mode="before")
    @classmethod
    def normalize_file_key(cls, value: str) -> str:
        return str(value or "").strip().strip("/")

    @model_validator(mode="after")
    def validate_qty_precision(self) -> "PurchaseOrderWarehouseOutboundRequest":
        try:
            qty = Decimal(str(self.actual_outbound_qty))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("实际出库数量格式不正确") from exc
        if qty.as_tuple().exponent < -4:
            raise ValueError("实际出库数量最多保留4位小数")
        return self


class PurchaseOrderAbnormalCloseRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("异常关闭原因不能为空")
        return text


class PurchaseOrderListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_no: str
    order_date: date
    sales_order_id: int
    sales_order_no: str
    purchase_contract_id: int | None
    purchase_contract_no: str | None
    supplier_company_id: int | None
    supplier_company_name: str | None
    warehouse_id: int
    warehouse_name: str
    product_id: int
    product_name: str
    qty_ton: float
    unit_price_tax_included: float | None
    amount_tax_included: float | None
    amount_tax_excluded: float | None
    tax_amount: float | None
    status: PurchaseOrderV5Status
    actual_outbound_qty_ton: float
    delivery_instruction_template_id: int | None
    delivery_instruction_template_name: str | None
    delivery_instruction_pdf_file_key: str | None
    delivery_instruction_pdf_file_url: str | None
    delivery_instruction_pdf_file_name: str | None = None
    supplier_payment_voucher_file_key: str | None
    supplier_payment_voucher_file_url: str | None
    supplier_delivery_doc_file_key: str | None
    supplier_delivery_doc_file_url: str | None
    supplier_delivery_doc_file_name: str | None = None
    outbound_doc_file_key: str | None
    outbound_doc_file_url: str | None
    outbound_doc_file_name: str | None = None
    closed_reason: str | None
    closed_by: int | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PurchaseOrderDetailOut(PurchaseOrderListItemOut):
    buyer_company_name: str | None = None
    seller_company_name: str | None = None
    contract_signing_subject_name: str | None = None
    sales_order_status: str
    customer_company_id: int | None
    customer_company_name: str | None
    sales_contract_id: int | None
    sales_contract_no: str | None
    confirm_snapshot: dict[str, object] | None
    confirm_acknowledged: bool
    purchase_contract_snapshot: dict[str, object] | None
    delivery_instruction_template_snapshot: dict[str, object] | None
    contract_confirmed_by: int | None
    contract_confirmed_at: datetime | None
    supplier_paid_by: int | None
    supplier_paid_at: datetime | None
    supplier_reviewed_by: int | None
    supplier_reviewed_at: datetime | None
    warehouse_reviewed_by: int | None
    warehouse_reviewed_at: datetime | None
    # 额外的付款凭证附件列表（第2个及以上），每项含 file_key 与 file_url
    supplier_payment_voucher_attachments: list[dict[str, str]] | None = None
