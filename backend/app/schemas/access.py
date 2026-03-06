from pydantic import BaseModel, Field


class AccessCheckRequest(BaseModel):
    role_code: str = Field(min_length=1, max_length=32, description="角色编码")
    company_type: str = Field(min_length=1, max_length=32, description="公司类型")
    client_type: str = Field(pattern="^(admin_web|miniprogram)$", description="端类型")


class AccessCheckResponse(BaseModel):
    allowed: bool
    message: str
