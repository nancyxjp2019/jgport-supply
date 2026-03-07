from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings

TEST_AUTH_SECRET = "CODEX-TEST-AUTH-SECRET"
BASE_DATABASE_URL = get_settings().database_url
TEST_DATABASE_NAME = f"jgport_v6_test_{uuid4().hex[:8]}"
TEST_DATABASE_URL = (
    make_url(BASE_DATABASE_URL)
    .set(database=TEST_DATABASE_NAME)
    .render_as_string(hide_password=False)
)
TEST_REPORT_EXPORT_DIR = BACKEND_DIR / f"CODEX-TEST-report-exports-{uuid4().hex[:8]}"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["AUTH_PROXY_SHARED_SECRET"] = TEST_AUTH_SECRET
os.environ["REPORT_EXPORT_DIR"] = str(TEST_REPORT_EXPORT_DIR)
get_settings.cache_clear()


def _build_admin_database_url(database_url: str) -> URL:
    return make_url(database_url).set(database="postgres")


def _create_test_database(database_url: str) -> None:
    admin_engine = create_engine(
        _build_admin_database_url(database_url), isolation_level="AUTOCOMMIT"
    )
    try:
        with admin_engine.connect() as connection:
            connection.execute(
                text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}" WITH (FORCE)')
            )
            connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))
    finally:
        admin_engine.dispose()


def _drop_test_database(database_url: str) -> None:
    admin_engine = create_engine(
        _build_admin_database_url(database_url), isolation_level="AUTOCOMMIT"
    )
    try:
        with admin_engine.connect() as connection:
            connection.execute(
                text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}" WITH (FORCE)')
            )
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database() -> None:
    _create_test_database(BASE_DATABASE_URL)
    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    yield
    from app.db.session import engine

    engine.dispose()
    _drop_test_database(BASE_DATABASE_URL)
    shutil.rmtree(TEST_REPORT_EXPORT_DIR, ignore_errors=True)


@pytest.fixture
def auth_headers() -> Callable[..., dict[str, str]]:
    def build_headers(
        *,
        user_id: str = "CODEX-TEST-ADMIN",
        role_code: str = "admin",
        company_id: str | None = None,
        company_type: str = "operator_company",
        client_type: str = "admin_web",
    ) -> dict[str, str]:
        resolved_company_id = company_id or _default_company_id(company_type)
        return {
            "X-User-Id": user_id,
            "X-Role-Code": role_code,
            "X-Company-Id": resolved_company_id,
            "X-Company-Type": company_type,
            "X-Client-Type": client_type,
            "X-Auth-Secret": TEST_AUTH_SECRET,
        }

    return build_headers


def _default_company_id(company_type: str) -> str:
    mapping = {
        "operator_company": "CODEX-TEST-OPERATOR-COMPANY",
        "customer_company": "CODEX-TEST-CUSTOMER-COMPANY",
        "supplier_company": "CODEX-TEST-SUPPLIER-COMPANY",
        "warehouse_company": "CODEX-TEST-WAREHOUSE-COMPANY",
    }
    return mapping.get(company_type, "CODEX-TEST-UNKNOWN-COMPANY")
