from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class BusinessLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: str | None
    user_id: int | None
    role: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    order_id: int | None
    before_status: str | None
    after_status: str | None
    result: str
    reason: str | None
    ip: str | None
    detail_json: dict[str, Any] | None
    created_at: datetime
