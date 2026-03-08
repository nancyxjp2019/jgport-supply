from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

COMPANY_TYPES = {
    "operator_company",
    "customer_company",
    "supplier_company",
    "warehouse_company",
}


class CompanyCreateRequest(BaseModel):
    company_id: str = Field(min_length=1, max_length=64, description="公司编码")
    company_name: str = Field(min_length=1, max_length=128, description="公司名称")
    company_type: str = Field(min_length=1, max_length=32, description="公司类型")
    parent_company_id: str | None = Field(
        default=None, min_length=1, max_length=64, description="归属运营商公司编码"
    )
    remark: str | None = Field(default=None, max_length=256, description="备注")

    @model_validator(mode="after")
    def validate_company_relation(self) -> "CompanyCreateRequest":
        _validate_company_type(self.company_type)
        if self.company_type == "operator_company" and self.parent_company_id:
            raise ValueError("运营商公司不能绑定上级公司")
        if self.company_type != "operator_company" and not self.parent_company_id:
            raise ValueError("非运营商公司必须绑定归属运营商")
        return self


class CompanyUpdateRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=128, description="公司名称")
    parent_company_id: str | None = Field(
        default=None, min_length=1, max_length=64, description="归属运营商公司编码"
    )
    remark: str | None = Field(default=None, max_length=256, description="备注")


class CompanyStatusUpdateRequest(BaseModel):
    enabled: bool = Field(description="是否启用")
    reason: str = Field(min_length=1, max_length=256, description="状态变更原因")


class CompanyListItemResponse(BaseModel):
    company_id: str
    company_name: str
    company_type: str
    parent_company_id: str | None = None
    parent_company_name: str | None = None
    status: str
    is_active: bool
    remark: str | None = None
    child_company_count: int = 0
    created_at: datetime
    updated_at: datetime


class CompanyDetailResponse(CompanyListItemResponse):
    created_by: str
    updated_by: str
    message: str


class CompanyListResponse(BaseModel):
    items: list[CompanyListItemResponse]
    total: int
    message: str


def _validate_company_type(company_type: str) -> None:
    if company_type not in COMPANY_TYPES:
        raise ValueError("公司类型不合法")
