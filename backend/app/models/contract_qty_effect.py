from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ContractQtyEffect(Base):
    __tablename__ = "contract_qty_effects"
    __table_args__ = (
        UniqueConstraint(
            "contract_item_id",
            "doc_type",
            "doc_id",
            "effect_type",
            name="uq_contract_qty_effect_unique",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_item_id: Mapped[int] = mapped_column(ForeignKey("contract_items.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    doc_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    effect_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    effect_qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    contract_item: Mapped["ContractItem"] = relationship()
