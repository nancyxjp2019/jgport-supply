from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.v5_domain import CompanyType, TemplateType


class AgreementTemplateSelectOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_code: str
    template_name: str
    template_type: TemplateType
    is_default: bool


class TransportProfileHistoryItemOut(BaseModel):
    id: int
    is_default: bool
    last_used_at: datetime | None
    transport_snapshot: dict[str, object]


class SalesContractSelectOptionOut(BaseModel):
    sales_contract_id: int
    contract_no: str
    customer_company_id: int
    customer_company_name: str
    product_id: int
    product_name: str
    unit_name: str
    pending_execution_qty_ton: float
    projected_pending_execution_qty_ton: float
    projected_over_execution_qty_ton: float


class PurchaseContractSelectOptionOut(BaseModel):
    purchase_contract_id: int
    contract_no: str
    supplier_company_id: int
    supplier_company_name: str
    product_id: int
    product_name: str
    unit_name: str
    pending_execution_qty_ton: float
    projected_pending_execution_qty_ton: float
    projected_over_execution_qty_ton: float
    default_sort_rank: int


class WarehouseSelectOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_code: str | None
    name: str


class ProductSelectOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_code: str | None
    name: str
    unit_name: str


class SalesOrderCreateWarehouseProductStockOut(BaseModel):
    warehouse_id: int
    product_id: int


class SalesOrderCreateMetaOut(BaseModel):
    order_creation_enabled: bool
    warehouses: list[WarehouseSelectOptionOut]
    products: list[ProductSelectOptionOut]
    sales_contracts: list[SalesContractSelectOptionOut]
    warehouse_product_stock_pairs: list[SalesOrderCreateWarehouseProductStockOut]


class CompanySelectOptionOut(BaseModel):
    id: int
    company_code: str
    company_name: str
    company_type: CompanyType


class PurchaseContractSelectQuery(BaseModel):
    product_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    qty: float = Field(gt=0)
