from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.v5_domain import TemplateStatus, TemplateType


class AgreementTemplateContentPayload(BaseModel):
    template_title: str | None = Field(default=None, max_length=128)
    template_content_json: dict[str, Any] = Field(default_factory=dict)
    placeholder_schema_json: dict[str, Any] = Field(default_factory=dict)
    render_config_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("template_title", mode="before")
    @classmethod
    def normalize_template_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value or "").strip()
        return text or None


class AgreementTemplateCreateRequest(AgreementTemplateContentPayload):
    template_type: TemplateType
    template_code: str = Field(min_length=1, max_length=64)
    template_name: str = Field(min_length=1, max_length=128)
    is_default: bool = False
    status: TemplateStatus = TemplateStatus.ENABLED
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("template_code", "template_name", "remark", mode="before")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value or "").strip()
        return text or None


class AgreementTemplateUpdateRequest(BaseModel):
    template_name: str | None = Field(default=None, min_length=1, max_length=128)
    remark: str | None = Field(default=None, max_length=255)
    template_title: str | None = Field(default=None, max_length=128)
    template_content_json: dict[str, Any] | None = None
    placeholder_schema_json: dict[str, Any] | None = None
    render_config_json: dict[str, Any] | None = None

    @field_validator("template_name", "remark", "template_title", mode="before")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value or "").strip()
        return text or None


class AgreementTemplateStatusUpdateRequest(BaseModel):
    status: TemplateStatus


class AgreementTemplateContentOut(BaseModel):
    template_title: str | None
    template_content_json: dict[str, Any]
    placeholder_schema_json: dict[str, Any]
    render_config_json: dict[str, Any]


class AgreementTemplateListItemOut(BaseModel):
    id: int
    template_type: TemplateType
    template_code: str
    template_name: str
    is_default: bool
    status: TemplateStatus
    remark: str | None
    created_by: int
    updated_by: int
    created_at: datetime
    updated_at: datetime


class AgreementTemplateDetailOut(AgreementTemplateListItemOut, AgreementTemplateContentOut):
    pass
