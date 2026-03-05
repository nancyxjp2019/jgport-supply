from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole, UserStatus


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str | None = Field(default=None, max_length=128)
    role: UserRole
    status: UserStatus = UserStatus.PENDING_ACTIVATION
    customer_id: int | None = None
    company_id: int | None = Field(default=None, gt=0)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        text = str(value or "").strip()
        if len(text) < 2:
            raise ValueError("用户名至少需要2个字符")
        return text


class UserStatusUpdate(BaseModel):
    status: UserStatus


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserProfileUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=64)
    display_name: str | None = Field(default=None, max_length=128)
    company_id: int | None = Field(default=None, gt=0)

    @field_validator("username")
    @classmethod
    def normalize_profile_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value or "").strip()
        if len(text) < 2:
            raise ValueError("用户名至少需要2个字符")
        return text


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None
    role: UserRole
    status: UserStatus
    customer_id: int | None
    company_id: int | None
    company_name_snapshot: str | None
    created_at: datetime
    updated_at: datetime


class ActivationLinkOut(BaseModel):
    user_id: int
    code: str
    expires_at: datetime
    activation_url: str
