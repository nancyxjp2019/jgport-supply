from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="草稿", index=True)
    supplier_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    threshold_release_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    threshold_over_exec_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    close_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    manual_close_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    manual_close_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manual_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    manual_close_diff_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    manual_close_diff_qty_json: Mapped[list[dict[str, str]] | None] = mapped_column(JSON, nullable=True)
    submit_comment: Mapped[str | None] = mapped_column(String(256), nullable=True)
    approval_comment: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    items: Mapped[list["ContractItem"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractItem.id",
    )
    effective_tasks: Mapped[list["ContractEffectiveTask"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractEffectiveTask.id",
    )
    receipt_docs: Mapped[list["ReceiptDoc"]] = relationship(
        back_populates="contract",
        order_by="ReceiptDoc.id",
    )
    payment_docs: Mapped[list["PaymentDoc"]] = relationship(
        back_populates="contract",
        order_by="PaymentDoc.id",
    )
    inbound_docs: Mapped[list["InboundDoc"]] = relationship(
        back_populates="contract",
        order_by="InboundDoc.id",
    )
    outbound_docs: Mapped[list["OutboundDoc"]] = relationship(
        back_populates="contract",
        order_by="OutboundDoc.id",
    )
