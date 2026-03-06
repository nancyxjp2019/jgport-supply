from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedActor:
    user_id: str
    role_code: str
    company_id: str | None
    company_type: str
    client_type: str
