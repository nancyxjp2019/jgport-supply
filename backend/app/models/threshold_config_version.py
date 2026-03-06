from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ThresholdConfigVersion(Base):
    __tablename__ = "threshold_config_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    threshold_release: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    threshold_over_exec: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="生效")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
