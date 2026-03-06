from decimal import Decimal

from pydantic import BaseModel, Field


class ThresholdConfigPublishRequest(BaseModel):
    threshold_release: Decimal = Field(gt=0, description="保证金放行阈值")
    threshold_over_exec: Decimal = Field(gt=0, description="合同超量履约阈值")
    reason: str = Field(min_length=1, max_length=256, description="变更原因")


class ThresholdConfigResponse(BaseModel):
    version: int
    threshold_release: Decimal
    threshold_over_exec: Decimal
    status: str
    message: str
