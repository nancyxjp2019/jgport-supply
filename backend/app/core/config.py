from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "JGPort V6 API"
    env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://davidxi@127.0.0.1:5432/jgport_v6"
    auth_proxy_shared_secret: str = "jgport-v6-dev-secret"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_value(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "off", "false", "0", "no"}:
                return False
            if normalized in {"debug", "dev", "test", "on", "true", "1", "yes"}:
                return True
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
