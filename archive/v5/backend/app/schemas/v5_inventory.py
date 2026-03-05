from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.v5_domain import (
    InventoryAdjustmentType,
    InventoryMovementType,
    PurchaseStockInSourceKind,
    PurchaseStockInStatus,
)


class PurchaseStockInConfirmRequest(BaseModel):
    warehouse_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    stock_in_qty: float = Field(gt=0)
    stock_in_date: date
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("remark", mode="before")
    @classmethod
    def normalize_remark(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class PurchaseStockInListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_in_no: str
    purchase_contract_id: int
    purchase_contract_no: str
    supplier_company_id: int
    supplier_company_name: str
    warehouse_id: int
    warehouse_name: str
    product_id: int
    product_name: str
    stock_in_qty_ton: float
    stock_in_date: date | None
    status: PurchaseStockInStatus
    source_kind: PurchaseStockInSourceKind
    remark: str | None
    confirmed_by: int | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PurchaseStockInDetailOut(PurchaseStockInListItemOut):
    purchase_contract_status: str
    purchase_contract_stocked_in_qty: float
    purchase_contract_pending_stock_in_qty: float


class InventoryAdjustmentCreateRequest(BaseModel):
    warehouse_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    adjust_type: InventoryAdjustmentType
    before_qty: float = Field(ge=0)
    adjust_qty: float = Field(gt=0)
    after_qty: float = Field(ge=0)
    reason: str = Field(min_length=1, max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("调整原因不能为空")
        return text

    @model_validator(mode="after")
    def validate_qty_relation(self) -> "InventoryAdjustmentCreateRequest":
        if self.adjust_type in {InventoryAdjustmentType.INCREASE, InventoryAdjustmentType.INITIALIZE}:
            expected_after = round(self.before_qty + self.adjust_qty, 4)
            if round(self.after_qty, 4) != expected_after:
                raise ValueError("库存调整后数量与变动数量不匹配")
        elif self.adjust_type == InventoryAdjustmentType.DECREASE:
            expected_after = round(self.before_qty - self.adjust_qty, 4)
            if expected_after < 0 or round(self.after_qty, 4) != expected_after:
                raise ValueError("库存减少后数量与变动数量不匹配")
        return self


class InventoryAdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    adjustment_no: str
    warehouse_id: int
    warehouse_name: str
    product_id: int
    product_name: str
    adjust_type: InventoryAdjustmentType
    before_qty_ton: float
    adjust_qty_ton: float
    after_qty_ton: float
    reason: str
    created_by: int
    created_at: datetime


class InventorySummaryWarehouseItemOut(BaseModel):
    warehouse_id: int
    warehouse_name: str
    total_on_hand_qty_ton: float
    total_reserved_qty_ton: float
    total_available_qty_ton: float
    low_stock_item_count: int
    product_items: list["InventorySummaryWarehouseProductItemOut"]


class InventorySummaryWarehouseProductItemOut(BaseModel):
    product_id: int
    product_name: str
    on_hand_qty_ton: float
    reserved_qty_ton: float
    available_qty_ton: float


class InventorySummaryProductWarehouseItemOut(BaseModel):
    warehouse_id: int
    warehouse_name: str
    on_hand_qty_ton: float
    reserved_qty_ton: float
    available_qty_ton: float


class InventorySummaryProductItemOut(BaseModel):
    product_id: int
    product_name: str
    total_on_hand_qty_ton: float
    total_reserved_qty_ton: float
    total_available_qty_ton: float
    warehouse_items: list[InventorySummaryProductWarehouseItemOut]


class InventorySummaryOut(BaseModel):
    total_on_hand_qty_ton: float
    total_reserved_qty_ton: float
    total_available_qty_ton: float
    low_stock_threshold: float
    warehouse_items: list[InventorySummaryWarehouseItemOut]
    product_items: list[InventorySummaryProductItemOut]


class InventoryMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movement_no: str
    warehouse_id: int
    warehouse_name: str
    product_id: int
    product_name: str
    movement_type: InventoryMovementType
    business_type: str
    business_id: int
    before_on_hand_qty_ton: float
    change_qty_ton: float
    after_on_hand_qty_ton: float
    before_reserved_qty_ton: float
    after_reserved_qty_ton: float
    remark: str | None
    operator_user_id: int
    operator_name: str | None
    created_at: datetime
