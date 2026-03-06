from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.business_audit_log import BusinessAuditLog


class AuditWriteFailedError(RuntimeError):
    """审计日志写入失败。"""


def write_audit_log_with_retry(
    session_factory: Callable[[], Session],
    payload: dict[str, Any],
    max_retries: int = 3,
) -> BusinessAuditLog:
    """写入审计日志，失败时按固定次数重试。"""
    last_error: Exception | None = None
    for _ in range(max_retries):
        session = session_factory()
        try:
            log = BusinessAuditLog(**payload)
            session.add(log)
            session.commit()
            session.refresh(log)
            return log
        except SQLAlchemyError as exc:
            session.rollback()
            last_error = exc
        finally:
            session.close()
    raise AuditWriteFailedError("审计日志写入失败，已达到最大重试次数") from last_error
