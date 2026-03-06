from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = BACKEND_DIR / ".env"
DEFAULT_DEV_AUTH_PROXY_SECRET = "jgport-v6-dev-secret"


class Settings(BaseSettings):
    app_name: str = "JGPort V6 API"
    env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://davidxi@127.0.0.1:5432/jgport_v6"
    auth_proxy_shared_secret: str = ""

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

    @model_validator(mode="after")
    def validate_auth_proxy_secret(self) -> "Settings":
        normalized_env = str(self.env or "").strip().lower()
        if not self.auth_proxy_shared_secret:
            if normalized_env in {"dev", "test"}:
                self.auth_proxy_shared_secret = DEFAULT_DEV_AUTH_PROXY_SECRET
                return self
            raise ValueError("非开发环境必须配置服务端身份透传密钥")
        if normalized_env not in {"dev", "test"} and self.auth_proxy_shared_secret == DEFAULT_DEV_AUTH_PROXY_SECRET:
            raise ValueError("非开发环境禁止使用默认服务端身份透传密钥")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
