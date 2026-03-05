from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.v5_domain import CompanyType


class CompanyCreateRequest(BaseModel):
    company_code: str = Field(min_length=1, max_length=64)
    company_name: str = Field(min_length=1, max_length=128)
    company_type: CompanyType
    tax_no: str | None = Field(default=None, max_length=64)
    contact_name: str | None = Field(default=None, max_length=64)
    contact_phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class CompanyUpdateRequest(BaseModel):
    company_code: str | None = Field(default=None, min_length=1, max_length=64)
    company_name: str | None = Field(default=None, min_length=1, max_length=128)
    company_type: CompanyType | None = None
    tax_no: str | None = Field(default=None, max_length=64)
    contact_name: str | None = Field(default=None, max_length=64)
    contact_phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class WarehouseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    warehouse_code: str | None = Field(default=None, max_length=64)
    company_id: int | None = Field(default=None, gt=0)
    is_active: bool = True


class WarehouseUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    warehouse_code: str | None = Field(default=None, max_length=64)
    company_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_code: str | None = None
    name: str
    company_id: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OilProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    product_code: str | None = Field(default=None, max_length=64)
    unit_name: str = Field(default="吨", min_length=1, max_length=16)
    is_active: bool = True


class OilProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    product_code: str | None = Field(default=None, max_length=64)
    unit_name: str | None = Field(default=None, min_length=1, max_length=16)
    is_active: bool | None = None


class OilProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_code: str | None = None
    name: str
    unit_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_code: str
    company_name: str
    company_type: CompanyType
    tax_no: str | None
    contact_name: str | None
    contact_phone: str | None
    address: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
