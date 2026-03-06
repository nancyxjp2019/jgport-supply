from pydantic import BaseModel, Field


class AccessCheckRequest(BaseModel):
    target_client_type: str = Field(
        pattern="^(admin_web|miniprogram)$",
        description="目标端类型",
    )


class AccessCheckResponse(BaseModel):
    allowed: bool
    message: str


class AccessMeResponse(BaseModel):
    user_id: str
    role_code: str
    company_id: str | None
    company_type: str
    client_type: str
    admin_web_allowed: bool
    miniprogram_allowed: bool
    message: str
