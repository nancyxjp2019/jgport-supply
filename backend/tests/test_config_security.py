from pydantic import ValidationError
import pytest

from app.core.config import Settings


def test_production_env_rejects_default_auth_proxy_secret() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            env='production',
            auth_proxy_shared_secret='jgport-v6-dev-secret',
            database_url='postgresql+psycopg://user@127.0.0.1:5432/jgport_v6',
        )
    assert '非开发环境禁止使用默认服务端身份透传密钥' in str(exc_info.value)


def test_dev_env_allows_blank_auth_proxy_secret() -> None:
    settings = Settings(
        env='dev',
        auth_proxy_shared_secret='',
        database_url='postgresql+psycopg://user@127.0.0.1:5432/jgport_v6',
    )
    assert settings.auth_proxy_shared_secret == 'jgport-v6-dev-secret'
