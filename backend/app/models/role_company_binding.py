from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RoleCompanyBinding(Base):
    __tablename__ = "role_company_bindings"
    __table_args__ = (
        UniqueConstraint("role_code", "company_type", "version", name="uq_role_company_binding_version"),
        Index(
            "uq_role_company_binding_active",
            "role_code",
            "company_type",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_code: Mapped[str] = mapped_column(String(32), nullable=False)
    company_type: Mapped[str] = mapped_column(String(32), nullable=False)
    admin_web_allowed: Mapped[bool] = mapped_column(nullable=False, default=False)
    miniprogram_allowed: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="生效")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
