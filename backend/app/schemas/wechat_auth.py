from pydantic import BaseModel, Field


class MiniProgramWeChatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128, description="微信登录临时凭证")


class MiniProgramWeChatLoginResponse(BaseModel):
    binding_required: bool
    access_token: str | None = None
    token_type: str | None = None
    expires_in_seconds: int | None = None
    user_id: str | None = None
    role_code: str | None = None
    company_id: str | None = None
    company_type: str | None = None
    client_type: str | None = None
    admin_web_allowed: bool | None = None
    miniprogram_allowed: bool | None = None
    openid_hint: str | None = None
    debug_openid: str | None = None
    message: str
