from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "JGSDSC Supply Chain API"
    env: str = "dev"
    debug: bool = True
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/jgsd_supply_chain"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    activation_code_expire_minutes: int = 1440
    activation_link_base_url: str = "https://your-domain.com/activate"
    wechat_login_mode: Literal["mock", "official"] = "mock"
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_api_base: str = "https://api.weixin.qq.com"
    wechat_api_timeout_seconds: int = 8

    file_storage_backend: str = "local"
    local_upload_dir: str = "./uploads"
    local_upload_base_url: str = "/media"
    upload_max_size_mb: int = 20
    oss_bucket_name: str = ""
    oss_endpoint: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_base_url: str = ""
    oss_prefix: str = "attachments"

    log_dir: str = "./logs"
    log_level: str = "INFO"
    log_retention_days: int = 30

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
    def normalize_local_paths(self) -> "Settings":
        self.database_url = self._normalize_database_url(self.database_url)
        self.local_upload_dir = self._normalize_backend_relative_path(self.local_upload_dir)
        self.log_dir = self._normalize_backend_relative_path(self.log_dir)
        return self

    @staticmethod
    def _normalize_backend_relative_path(raw_path: str) -> str:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return str(path.resolve())

    @staticmethod
    def _normalize_database_url(database_url: str) -> str:
        url = make_url(database_url)
        if not url.drivername.startswith("sqlite"):
            return database_url
        database = url.database
        if not database or database == ":memory:":
            return database_url
        database_path = Path(database).expanduser()
        if not database_path.is_absolute():
            database_path = BACKEND_DIR / database_path
        normalized_url = url.set(database=str(database_path.resolve()))
        return normalized_url.render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
