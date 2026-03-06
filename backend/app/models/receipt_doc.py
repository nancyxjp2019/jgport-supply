from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReceiptDoc(Base):
    __tablename__ = "receipt_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    doc_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False, index=True)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    amount_actual: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="草稿", index=True)
    voucher_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    voucher_exempt_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    refund_status: Mapped[str] = mapped_column(String(16), nullable=False, default="未退款")
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    contract: Mapped["Contract"] = relationship(back_populates="receipt_docs")
    sales_order: Mapped["SalesOrder | None"] = relationship(back_populates="receipt_docs")
