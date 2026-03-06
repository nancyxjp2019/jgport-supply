from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogCreateRequest(BaseModel):
    event_code: str = Field(min_length=1, max_length=64, description="事件编码")
    biz_type: str = Field(min_length=1, max_length=64, description="业务类型")
    biz_id: str = Field(min_length=1, max_length=64, description="业务ID")
    operator_id: str = Field(min_length=1, max_length=64, description="操作人ID")
    before_json: dict = Field(default_factory=dict, description="变更前")
    after_json: dict = Field(default_factory=dict, description="变更后")
    extra_json: dict = Field(default_factory=dict, description="扩展信息")


class AuditLogItem(BaseModel):
    id: int
    event_code: str
    biz_type: str
    biz_id: str
    operator_id: str
    before_json: dict
    after_json: dict
    extra_json: dict
    occurred_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
