from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.v5_domain import ContractStatus


class ContractItemIn(BaseModel):
    product_id: int = Field(gt=0)
    qty_ton: float = Field(gt=0)
    tax_rate: float = Field(default=0.0, ge=0)
    unit_price_tax_included: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_precision(self) -> "ContractItemIn":
        for raw_value, field_name in (
            (self.qty_ton, "合同数量"),
            (self.tax_rate, "税率"),
            (self.unit_price_tax_included, "含税单价"),
        ):
            try:
                Decimal(str(raw_value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError(f"{field_name}格式不正确") from exc
        return self


class SalesContractCreateRequest(BaseModel):
    contract_no: str = Field(min_length=1, max_length=64)
    customer_company_id: int = Field(gt=0)
    template_id: int = Field(gt=0)
    contract_date: date
    deposit_rate: float = Field(default=0.1, ge=0)
    variable_snapshot: dict[str, object] = Field(default_factory=dict)
    items: list[ContractItemIn] = Field(min_length=1, max_length=20)

    @field_validator("contract_no", mode="before")
    @classmethod
    def normalize_contract_no(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("合同号不能为空")
        return text


class SalesContractUpdateRequest(BaseModel):
    customer_company_id: int | None = Field(default=None, gt=0)
    template_id: int | None = Field(default=None, gt=0)
    contract_date: date | None = None
    deposit_rate: float | None = Field(default=None, ge=0)
    variable_snapshot: dict[str, object] | None = None
    items: list[ContractItemIn] | None = Field(default=None, min_length=1, max_length=20)


class PurchaseContractCreateRequest(BaseModel):
    contract_no: str = Field(min_length=1, max_length=64)
    supplier_company_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    template_id: int = Field(gt=0)
    contract_date: date
    deposit_rate: float = Field(default=0.1, ge=0)
    variable_snapshot: dict[str, object] = Field(default_factory=dict)
    items: list[ContractItemIn] = Field(min_length=1, max_length=20)

    @field_validator("contract_no", mode="before")
    @classmethod
    def normalize_contract_no(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("合同号不能为空")
        return text


class PurchaseContractUpdateRequest(BaseModel):
    supplier_company_id: int | None = Field(default=None, gt=0)
    warehouse_id: int | None = Field(default=None, gt=0)
    template_id: int | None = Field(default=None, gt=0)
    contract_date: date | None = None
    deposit_rate: float | None = Field(default=None, ge=0)
    variable_snapshot: dict[str, object] | None = None
    items: list[ContractItemIn] | None = Field(default=None, min_length=1, max_length=20)


class ContractSubmitEffectiveRequest(BaseModel):
    signed_contract_file_key: str = Field(min_length=1, max_length=255)
    deposit_receipt_file_key: str = Field(min_length=1, max_length=255)

    @field_validator("signed_contract_file_key", "deposit_receipt_file_key", mode="before")
    @classmethod
    def normalize_file_key(cls, value: str) -> str:
        return str(value or "").strip().strip("/")


class ContractVoidRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("作废原因不能为空")
        return text


class ContractItemOut(BaseModel):
    product_id: int
    product_name: str
    qty_ton: float
    unit_name: str
    tax_rate: float
    unit_price_tax_included: float
    amount_tax_included: float
    amount_tax_excluded: float
    tax_amount: float


class SalesContractListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_no: str
    customer_company_id: int
    customer_company_name: str
    product_name: str
    template_id: int
    template_name: str
    contract_date: date
    status: ContractStatus
    item_count: int
    contract_items: list[ContractItemOut]
    deposit_rate: float
    deposit_amount: float
    base_contract_qty: float
    effective_contract_qty: float
    executed_qty: float
    pending_execution_qty: float
    over_executed_qty: float
    signed_contract_file_key: str | None
    signed_contract_file_url: str | None
    deposit_receipt_file_key: str | None
    deposit_receipt_file_url: str | None
    generated_pdf_file_key: str | None
    generated_pdf_file_url: str | None
    effective_at: datetime | None
    effective_by: int | None
    voided_at: datetime | None
    voided_by: int | None
    created_at: datetime
    updated_at: datetime


class SalesContractDetailOut(SalesContractListItemOut):
    variable_snapshot: dict[str, object]
    template_snapshot: dict[str, object]
    items: list[ContractItemOut]


class PurchaseContractListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_no: str
    supplier_company_id: int
    supplier_company_name: str
    product_name: str
    warehouse_id: int
    warehouse_name: str
    template_id: int
    template_name: str
    contract_date: date
    status: ContractStatus
    item_count: int
    contract_items: list[ContractItemOut]
    deposit_rate: float
    deposit_amount: float
    base_contract_qty: float
    effective_contract_qty: float
    executed_qty: float
    pending_execution_qty: float
    over_executed_qty: float
    stocked_in_qty: float
    pending_stock_in_qty: float
    signed_contract_file_key: str | None
    signed_contract_file_url: str | None
    deposit_receipt_file_key: str | None
    deposit_receipt_file_url: str | None
    generated_pdf_file_key: str | None
    generated_pdf_file_url: str | None
    effective_at: datetime | None
    effective_by: int | None
    voided_at: datetime | None
    voided_by: int | None
    created_at: datetime
    updated_at: datetime


class PurchaseContractDetailOut(PurchaseContractListItemOut):
    variable_snapshot: dict[str, object]
    template_snapshot: dict[str, object]
    items: list[ContractItemOut]


class ContractPdfOut(BaseModel):
    file_key: str
    file_url: str
