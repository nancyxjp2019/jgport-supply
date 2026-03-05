from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.log_context import get_log_context

_LOGGING_READY = False
_RESERVED_KEYS = set(logging.makeLogRecord({}).__dict__.keys()) | {
    "asctime",
    "message",
    "color_message",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(self._build_context())
        payload.update(self._extract_extra(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _build_context() -> dict[str, Any]:
        context = get_log_context()
        return {k: v for k, v in context.items() if v is not None}

    @staticmethod
    def _extract_extra(record: logging.LogRecord) -> dict[str, Any]:
        extra: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in _RESERVED_KEYS or key.startswith("_"):
                continue
            extra[key] = value
        return extra


def _resolve_level(level_name: str) -> int:
    level = logging.getLevelName(level_name.upper())
    if isinstance(level, int):
        return level
    return logging.INFO


def _build_file_handler(
    file_path: Path,
    level: int,
    retention_days: int,
    formatter: logging.Formatter,
) -> TimedRotatingFileHandler:
    handler = TimedRotatingFileHandler(
        filename=file_path,
        when="midnight",
        interval=1,
        backupCount=retention_days,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def _configure_logger(name: str, level: int, handlers: list[logging.Handler]) -> None:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    for handler in handlers:
        logger.addHandler(handler)
    logger.propagate = False


def setup_logging() -> None:
    global _LOGGING_READY
    if _LOGGING_READY:
        return

    settings = get_settings()
    log_level = _resolve_level(settings.log_level)
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    json_formatter = JsonFormatter()
    text_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(text_formatter)

    app_handler = _build_file_handler(
        file_path=log_dir / "app.log",
        level=log_level,
        retention_days=settings.log_retention_days,
        formatter=json_formatter,
    )
    error_handler = _build_file_handler(
        file_path=log_dir / "error.log",
        level=logging.ERROR,
        retention_days=settings.log_retention_days,
        formatter=json_formatter,
    )
    access_handler = _build_file_handler(
        file_path=log_dir / "access.log",
        level=log_level,
        retention_days=settings.log_retention_days,
        formatter=json_formatter,
    )
    business_handler = _build_file_handler(
        file_path=log_dir / "business.log",
        level=log_level,
        retention_days=settings.log_retention_days,
        formatter=json_formatter,
    )

    _configure_logger("app.system", log_level, [console_handler, app_handler, error_handler])
    _configure_logger("app.access", log_level, [console_handler, access_handler])
    _configure_logger("app.business", log_level, [console_handler, business_handler])
    _configure_logger("uvicorn.error", log_level, [console_handler, app_handler, error_handler])
    _configure_logger("uvicorn.access", log_level, [console_handler, access_handler])

    _LOGGING_READY = True


def get_system_logger() -> logging.Logger:
    return logging.getLogger("app.system")


def get_access_logger() -> logging.Logger:
    return logging.getLogger("app.access")


def get_business_logger() -> logging.Logger:
    return logging.getLogger("app.business")
