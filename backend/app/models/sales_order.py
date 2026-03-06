from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    sales_contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False, index=True)
    oil_product_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    qty_ordered: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="草稿", index=True)
    submit_comment: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ops_comment: Mapped[str | None] = mapped_column(String(256), nullable=True)
    finance_comment: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    ops_approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finance_approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ops_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finance_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        back_populates="sales_order",
        order_by="PurchaseOrder.id",
    )
    derivative_tasks: Mapped[list["SalesOrderDerivativeTask"]] = relationship(
        back_populates="sales_order",
        cascade="all, delete-orphan",
        order_by="SalesOrderDerivativeTask.id",
    )
    receipt_docs: Mapped[list["ReceiptDoc"]] = relationship(
        back_populates="sales_order",
        order_by="ReceiptDoc.id",
    )
