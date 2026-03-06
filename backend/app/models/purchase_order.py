from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    purchase_contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_sales_order_id: Mapped[int] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    supplier_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    oil_product_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    qty_ordered: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="已创建", index=True)
    zero_pay_exception_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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

    sales_order: Mapped["SalesOrder"] = relationship(back_populates="purchase_orders")
