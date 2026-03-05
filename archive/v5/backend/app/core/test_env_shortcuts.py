from __future__ import annotations

from app.core.config import get_settings


def _normalized_env() -> str:
    return (get_settings().env or "").strip().lower()


def is_non_prod_env() -> bool:
    return _normalized_env() not in {"prod", "production"}


def is_test_env() -> bool:
    return _normalized_env() == "test"
