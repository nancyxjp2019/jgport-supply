from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class InboundDocSubmitRequest(BaseModel):
    actual_qty: Decimal = Field(gt=0, description="实际入库数量")
    warehouse_id: str = Field(min_length=1, max_length=64, description="仓库ID")


class OutboundDocSubmitRequest(BaseModel):
    actual_qty: Decimal = Field(gt=0, description="实际出库数量")
    warehouse_id: str = Field(min_length=1, max_length=64, description="仓库ID")


class OutboundDocWarehouseConfirmRequest(BaseModel):
    contract_id: int = Field(gt=0, description="销售合同ID")
    sales_order_id: int = Field(gt=0, description="销售订单ID")
    source_ticket_no: str = Field(
        min_length=1, max_length=64, description="仓库来源回执号"
    )
    actual_qty: Decimal = Field(gt=0, description="实际出库数量")
    warehouse_id: str = Field(min_length=1, max_length=64, description="仓库ID")


class OutboundDocManualCreateRequest(BaseModel):
    contract_id: int = Field(gt=0, description="销售合同ID")
    sales_order_id: int = Field(gt=0, description="销售订单ID")
    oil_product_id: str = Field(min_length=1, max_length=64, description="油品ID")
    manual_ref_no: str = Field(min_length=1, max_length=64, description="手工回执号")
    actual_qty: Decimal = Field(gt=0, description="实际出库数量")
    reason: str = Field(min_length=1, max_length=256, description="手工补录原因")


class InboundDocResponse(BaseModel):
    id: int
    doc_no: str
    contract_id: int
    purchase_order_id: int | None = None
    oil_product_id: str
    warehouse_id: str | None = None
    source_type: str
    actual_qty: Decimal
    status: str
    submitted_at: datetime | None = None
    created_at: datetime
    message: str


class OutboundDocResponse(BaseModel):
    id: int
    doc_no: str
    contract_id: int
    sales_order_id: int
    oil_product_id: str
    warehouse_id: str | None = None
    source_type: str
    source_ticket_no: str | None = None
    manual_ref_no: str | None = None
    actual_qty: Decimal
    status: str
    submitted_at: datetime | None = None
    created_at: datetime
    message: str


class InboundDocListItem(BaseModel):
    id: int
    doc_no: str
    contract_id: int
    purchase_order_id: int | None = None
    oil_product_id: str
    warehouse_id: str | None = None
    source_type: str
    actual_qty: Decimal
    status: str
    submitted_at: datetime | None = None
    created_at: datetime


class OutboundDocListItem(BaseModel):
    id: int
    doc_no: str
    contract_id: int
    sales_order_id: int
    oil_product_id: str
    warehouse_id: str | None = None
    source_type: str
    source_ticket_no: str | None = None
    manual_ref_no: str | None = None
    actual_qty: Decimal
    status: str
    submitted_at: datetime | None = None
    created_at: datetime


class InboundDocListResponse(BaseModel):
    items: list[InboundDocListItem]
    total: int
    message: str


class OutboundDocListResponse(BaseModel):
    items: list[OutboundDocListItem]
    total: int
    message: str
