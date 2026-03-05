from pathlib import Path

from alembic import command
from alembic.config import Config

import app.models  # noqa: F401

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine


def run_migrations() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    alembic_ini_path = backend_dir / "alembic.ini"
    if not alembic_ini_path.exists():
        Base.metadata.create_all(bind=engine)
        return

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(alembic_cfg, "head")


def init_db() -> None:
    run_migrations()
