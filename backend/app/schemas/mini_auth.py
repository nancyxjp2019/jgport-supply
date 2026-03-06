from pydantic import BaseModel, Field


class MiniProgramDevLoginRequest(BaseModel):
    role_code: str = Field(
        pattern="^(operations|finance|admin|customer|supplier|warehouse)$",
        description="本地联调角色编码",
    )


class MiniProgramDevLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in_seconds: int
    user_id: str
    role_code: str
    company_id: str | None
    company_type: str
    client_type: str
    admin_web_allowed: bool
    miniprogram_allowed: bool
    message: str
