from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    company_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    company_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    parent_company_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("company_profiles.company_id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="启用", index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
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

    parent_company: Mapped[CompanyProfile | None] = relationship(
        remote_side="CompanyProfile.company_id",
        back_populates="child_companies",
    )
    child_companies: Mapped[list[CompanyProfile]] = relationship(
        back_populates="parent_company",
    )
