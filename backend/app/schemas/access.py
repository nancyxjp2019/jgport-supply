from pydantic import BaseModel, Field


class AccessCheckRequest(BaseModel):
    target_client_type: str = Field(
        pattern="^(admin_web|miniprogram)$",
        description="目标端类型",
    )


class AccessCheckResponse(BaseModel):
    allowed: bool
    message: str
