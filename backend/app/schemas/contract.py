from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ContractItemPayload(BaseModel):
    oil_product_id: str = Field(min_length=1, max_length=64, description="油品ID")
    qty_signed: Decimal = Field(gt=0, description="签约数量")
    unit_price: Decimal = Field(gt=0, description="合同单价")


class PurchaseContractCreateRequest(BaseModel):
    contract_no: str = Field(min_length=1, max_length=64, description="合同编号")
    supplier_id: str = Field(min_length=1, max_length=64, description="供应商ID")
    items: list[ContractItemPayload] = Field(min_length=1, description="采购合同明细")

    @model_validator(mode="after")
    def validate_items(self) -> "PurchaseContractCreateRequest":
        _validate_unique_oil_products(self.items)
        return self


class SalesContractCreateRequest(BaseModel):
    contract_no: str = Field(min_length=1, max_length=64, description="合同编号")
    customer_id: str = Field(min_length=1, max_length=64, description="客户ID")
    items: list[ContractItemPayload] = Field(min_length=1, description="销售合同明细")

    @model_validator(mode="after")
    def validate_items(self) -> "SalesContractCreateRequest":
        _validate_unique_oil_products(self.items)
        return self


class ContractSubmitRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=256, description="提交说明")


class ContractApproveRequest(BaseModel):
    approval_result: bool = Field(description="审批结果")
    comment: str = Field(min_length=1, max_length=256, description="审批意见")


class ContractManualCloseRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=256, description="手工关闭原因")
    confirm_token: str = Field(
        min_length=1, max_length=32, description="手工关闭确认口令"
    )


class ContractItemResponse(BaseModel):
    id: int
    oil_product_id: str
    qty_signed: Decimal
    unit_price: Decimal
    qty_in_acc: Decimal
    qty_out_acc: Decimal


class ContractResponse(BaseModel):
    id: int
    contract_no: str
    direction: str
    status: str
    supplier_id: str | None = None
    customer_id: str | None = None
    threshold_release_snapshot: Decimal | None = None
    threshold_over_exec_snapshot: Decimal | None = None
    close_type: str | None = None
    closed_by: str | None = None
    closed_at: datetime | None = None
    manual_close_reason: str | None = None
    manual_close_by: str | None = None
    manual_close_at: datetime | None = None
    manual_close_diff_amount: Decimal | None = None
    manual_close_diff_qty_json: list[dict[str, str]] | None = None
    submit_comment: str | None = None
    approval_comment: str | None = None
    approved_by: str | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    items: list[ContractItemResponse]
    generated_task_count: int = 0
    message: str


class ContractListItemResponse(BaseModel):
    id: int
    contract_no: str
    direction: str
    status: str
    supplier_id: str | None = None
    customer_id: str | None = None
    close_type: str | None = None
    closed_by: str | None = None
    closed_at: datetime | None = None
    manual_close_reason: str | None = None
    manual_close_by: str | None = None
    manual_close_at: datetime | None = None
    manual_close_diff_amount: Decimal | None = None
    manual_close_diff_qty_json: list[dict[str, str]] | None = None
    created_at: datetime


class ContractListResponse(BaseModel):
    items: list[ContractListItemResponse]
    total: int
    message: str


class ContractEffectiveTaskResponse(BaseModel):
    id: int
    target_doc_type: str
    status: str
    idempotency_key: str


class ContractGraphResponse(BaseModel):
    contract_id: int
    contract_no: str
    direction: str
    status: str
    downstream_tasks: list[ContractEffectiveTaskResponse]
    message: str


def _validate_unique_oil_products(items: list[ContractItemPayload]) -> None:
    oil_product_ids = [item.oil_product_id for item in items]
    if len(oil_product_ids) != len(set(oil_product_ids)):
        raise ValueError("同一合同下油品明细不能重复")
