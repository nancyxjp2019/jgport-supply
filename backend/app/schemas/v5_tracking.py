from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.v5_domain import SalesOrderV5Status


class V5ProgressNodeOut(BaseModel):
    node_code: str
    node_name: str
    status: str
    operator: str | None = None
    finished_at: datetime | None = None
    block_reason: str | None = None


class V5SalesOrderProgressOut(BaseModel):
    order_id: int
    status: SalesOrderV5Status
    nodes: list[V5ProgressNodeOut]


class V5OrderLogOut(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    action: str
    action_name: str
    operator_user_id: int | None = None
    operator_name: str | None = None
    role: str | None = None
    before_status: str | None = None
    after_status: str | None = None
    reason: str | None = None
    detail_json: dict[str, Any] | None = None
    created_at: datetime
