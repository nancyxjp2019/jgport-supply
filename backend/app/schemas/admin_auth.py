from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SuperAdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class SuperAdminLoginResponse(BaseModel):
    mfa_required: bool = True
    challenge_token: str | None = None
    challenge_expires_in: int | None = None
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    super_admin: SuperAdminOut | None = None


class SuperAdminTotpVerifyRequest(BaseModel):
    challenge_token: str = Field(min_length=1)
    totp_code: str = Field(min_length=1, max_length=6)


class SuperAdminRecoveryVerifyRequest(BaseModel):
    challenge_token: str = Field(min_length=1)
    recovery_code: str = Field(min_length=4, max_length=32)


class SuperAdminOut(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class SuperAdminAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    super_admin: SuperAdminOut


class SuperAdminLogoutResponse(BaseModel):
    success: bool = True
