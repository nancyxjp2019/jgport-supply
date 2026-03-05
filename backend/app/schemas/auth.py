from pydantic import BaseModel, Field

from app.schemas.user import UserOut


class WeChatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)


class WeChatBindRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)
    activation_code: str = Field(min_length=1, max_length=64)


class WeChatLoginResponse(BaseModel):
    activation_required: bool = False
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    user: UserOut | None = None
    openid_hint: str | None = None
