from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InboundDoc(Base):
    __tablename__ = "inbound_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False, index=True)
    purchase_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    oil_product_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    actual_qty: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False, default=Decimal("0.000"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="草稿", index=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    contract: Mapped["Contract"] = relationship(back_populates="inbound_docs")
    purchase_order: Mapped["PurchaseOrder | None"] = relationship(back_populates="inbound_docs")
