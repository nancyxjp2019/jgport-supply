from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")
AMOUNT_TYPE = Numeric(18, 2)
QTY_TYPE = Numeric(18, 4)
RATE_TYPE = Numeric(5, 4)


class TemplateType(str, Enum):
    DELIVERY_INSTRUCTION = "DELIVERY_INSTRUCTION"
    SALES_CONTRACT = "SALES_CONTRACT"
    PURCHASE_CONTRACT = "PURCHASE_CONTRACT"


class TemplateStatus(str, Enum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class CompanyType(str, Enum):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"
    OPERATOR = "OPERATOR"
    WAREHOUSE = "WAREHOUSE"


class ContractStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_EFFECTIVE = "PENDING_EFFECTIVE"
    EFFECTIVE = "EFFECTIVE"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    COMPLETED = "COMPLETED"
    VOIDED = "VOIDED"


class ContractKind(str, Enum):
    PRIMARY = "PRIMARY"
    SUPPLEMENT = "SUPPLEMENT"


class SalesOrderV5Status(str, Enum):
    SUBMITTED = "SUBMITTED"
    OPERATOR_APPROVED = "OPERATOR_APPROVED"
    CUSTOMER_PAYMENT_CONFIRMED = "CUSTOMER_PAYMENT_CONFIRMED"
    READY_FOR_OUTBOUND = "READY_FOR_OUTBOUND"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    ABNORMAL_CLOSED = "ABNORMAL_CLOSED"


class PurchaseOrderV5Status(str, Enum):
    PENDING_SUBMIT = "PENDING_SUBMIT"
    SUPPLIER_PAYMENT_PENDING = "SUPPLIER_PAYMENT_PENDING"
    SUPPLIER_REVIEW_PENDING = "SUPPLIER_REVIEW_PENDING"
    WAREHOUSE_PENDING = "WAREHOUSE_PENDING"
    COMPLETED = "COMPLETED"
    ABNORMAL_CLOSED = "ABNORMAL_CLOSED"


class PurchaseStockInStatus(str, Enum):
    PENDING_CONFIRM = "PENDING_CONFIRM"
    CONFIRMED = "CONFIRMED"
    VOIDED = "VOIDED"


class PurchaseStockInSourceKind(str, Enum):
    PRIMARY_AUTO = "PRIMARY_AUTO"
    SUPPLEMENT_AUTO = "SUPPLEMENT_AUTO"
    MANUAL_APPEND = "MANUAL_APPEND"


class SalesInventoryReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    CONSUMED = "CONSUMED"


class InventoryMovementType(str, Enum):
    PURCHASE_STOCK_IN = "PURCHASE_STOCK_IN"
    PURCHASE_SUPPLEMENT_STOCK_IN = "PURCHASE_SUPPLEMENT_STOCK_IN"
    SALES_RESERVE = "SALES_RESERVE"
    SALES_RESERVE_RELEASE = "SALES_RESERVE_RELEASE"
    SALES_OUTBOUND = "SALES_OUTBOUND"
    INVENTORY_ADJUSTMENT = "INVENTORY_ADJUSTMENT"


class InventoryAdjustmentType(str, Enum):
    INITIALIZE = "INITIALIZE"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"


class StorageBackend(str, Enum):
    LOCAL = "LOCAL"
    OSS = "OSS"


class ReportType(str, Enum):
    SALES_ORDERS = "SALES_ORDERS"
    PURCHASE_ORDERS = "PURCHASE_ORDERS"
    SALES_CONTRACTS = "SALES_CONTRACTS"
    PURCHASE_CONTRACTS = "PURCHASE_CONTRACTS"
    INVENTORY_MOVEMENTS = "INVENTORY_MOVEMENTS"
    WAREHOUSE_LEDGER = "WAREHOUSE_LEDGER"


class ReportExportStatus(str, Enum):
    GENERATED = "GENERATED"
    FAILED = "FAILED"


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        Index("idx_companies_type_name", "company_type", "company_name"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    company_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    company_type: Mapped[CompanyType] = mapped_column(
        SQLEnum(CompanyType, native_enum=False),
        nullable=False,
        index=True,
    )
    tax_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AgreementTemplate(Base):
    __tablename__ = "agreement_templates"
    __table_args__ = (
        Index("idx_agreement_templates_type_status_default", "template_type", "status", "is_default"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    template_type: Mapped[TemplateType] = mapped_column(
        SQLEnum(TemplateType, native_enum=False),
        nullable=False,
        index=True,
    )
    template_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    template_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    status: Mapped[TemplateStatus] = mapped_column(
        SQLEnum(TemplateStatus, native_enum=False),
        nullable=False,
        default=TemplateStatus.ENABLED,
        index=True,
    )
    current_version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AgreementTemplateVersion(Base):
    __tablename__ = "agreement_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_no", name="uk_agreement_template_versions_template_version"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("agreement_templates.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    template_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_content_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    placeholder_schema_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    render_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SalesContract(Base):
    __tablename__ = "sales_contracts"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    contract_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    contract_kind: Mapped[ContractKind] = mapped_column(
        SQLEnum(ContractKind, native_enum=False),
        nullable=False,
        default=ContractKind.PRIMARY,
        index=True,
    )
    source_contract_id: Mapped[int | None] = mapped_column(ForeignKey("sales_contracts.id"), nullable=True, index=True)
    customer_company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("agreement_templates.id"), nullable=False)
    template_version_id: Mapped[int] = mapped_column(ForeignKey("agreement_template_versions.id"), nullable=False)
    template_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    variable_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    signed_contract_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    deposit_receipt_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    contract_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[ContractStatus] = mapped_column(
        SQLEnum(ContractStatus, native_enum=False),
        nullable=False,
        default=ContractStatus.DRAFT,
        index=True,
    )
    deposit_rate: Mapped[Decimal] = mapped_column(RATE_TYPE, nullable=False, default=Decimal("0.1000"))
    deposit_amount: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False, default=Decimal("0.00"))
    base_contract_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    supplement_qty_total: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    effective_contract_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    executed_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    pending_execution_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    over_executed_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SalesContractItem(Base):
    __tablename__ = "sales_contract_items"
    __table_args__ = (
        UniqueConstraint("sales_contract_id", "product_id", name="uk_sales_contract_items_contract_product"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    sales_contract_id: Mapped[int] = mapped_column(ForeignKey("sales_contracts.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("oil_products.id"), nullable=False, index=True)
    qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    unit_name: Mapped[str] = mapped_column(String(16), nullable=False, default="吨")
    tax_rate: Mapped[Decimal] = mapped_column(RATE_TYPE, nullable=False, default=Decimal("0.0000"))
    unit_price_tax_included: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    amount_tax_included: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    amount_tax_excluded: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PurchaseContract(Base):
    __tablename__ = "purchase_contracts"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    contract_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    contract_kind: Mapped[ContractKind] = mapped_column(
        SQLEnum(ContractKind, native_enum=False),
        nullable=False,
        default=ContractKind.PRIMARY,
        index=True,
    )
    source_contract_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_contracts.id"), nullable=True, index=True)
    supplier_company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("agreement_templates.id"), nullable=False)
    template_version_id: Mapped[int] = mapped_column(ForeignKey("agreement_template_versions.id"), nullable=False)
    template_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    variable_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    signed_contract_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    deposit_receipt_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    contract_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[ContractStatus] = mapped_column(
        SQLEnum(ContractStatus, native_enum=False),
        nullable=False,
        default=ContractStatus.DRAFT,
        index=True,
    )
    deposit_rate: Mapped[Decimal] = mapped_column(RATE_TYPE, nullable=False, default=Decimal("0.1000"))
    deposit_amount: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False, default=Decimal("0.00"))
    base_contract_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    supplement_qty_total: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    effective_contract_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    executed_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    pending_execution_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    over_executed_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    stocked_in_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    pending_stock_in_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PurchaseContractItem(Base):
    __tablename__ = "purchase_contract_items"
    __table_args__ = (
        UniqueConstraint("purchase_contract_id", "product_id", name="uk_purchase_contract_items_contract_product"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    purchase_contract_id: Mapped[int] = mapped_column(ForeignKey("purchase_contracts.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("oil_products.id"), nullable=False, index=True)
    qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    unit_name: Mapped[str] = mapped_column(String(16), nullable=False, default="吨")
    tax_rate: Mapped[Decimal] = mapped_column(RATE_TYPE, nullable=False, default=Decimal("0.0000"))
    unit_price_tax_included: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    amount_tax_included: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    amount_tax_excluded: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ContractExecutionLog(Base):
    __tablename__ = "contract_execution_logs"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    contract_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    contract_id: Mapped[int] = mapped_column(ID_TYPE, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(ID_TYPE, nullable=False, index=True)
    qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    before_executed_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    after_executed_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    before_pending_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    after_pending_qty: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CustomerTransportProfile(Base):
    __tablename__ = "customer_transport_profiles"
    __table_args__ = (
        Index("idx_customer_transport_profiles_customer_last_used", "customer_company_id", "last_used_at"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    customer_company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    transport_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SalesOrderV5(Base):
    __tablename__ = "sales_orders"
    __table_args__ = (
        Index("idx_sales_orders_customer_status_date", "customer_company_id", "status", "order_date"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    sales_order_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    customer_company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("oil_products.id"), nullable=False, index=True)
    sales_contract_id: Mapped[int] = mapped_column(ForeignKey("sales_contracts.id"), nullable=False, index=True)
    sales_contract_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    unit_price_tax_included: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    amount_tax_included: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    operator_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    operator_company_name_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    transport_profile_id: Mapped[int | None] = mapped_column(ForeignKey("customer_transport_profiles.id"), nullable=True)
    transport_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_amount: Mapped[Decimal | None] = mapped_column(AMOUNT_TYPE, nullable=True)
    customer_payment_receipt_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    reserved_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    actual_outbound_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    status: Mapped[SalesOrderV5Status] = mapped_column(
        SQLEnum(SalesOrderV5Status, native_enum=False),
        nullable=False,
        default=SalesOrderV5Status.SUBMITTED,
        index=True,
    )
    operator_reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    operator_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finance_reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    finance_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PurchaseOrderV5(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index("idx_purchase_orders_status_supplier_warehouse", "status", "supplier_company_id", "warehouse_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    purchase_order_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, unique=True, index=True)
    purchase_contract_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_contracts.id"), nullable=True, index=True)
    purchase_contract_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    supplier_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("oil_products.id"), nullable=False, index=True)
    qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    unit_price_tax_included: Mapped[Decimal | None] = mapped_column(AMOUNT_TYPE, nullable=True)
    amount_tax_included: Mapped[Decimal | None] = mapped_column(AMOUNT_TYPE, nullable=True)
    confirm_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confirm_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivery_instruction_template_id: Mapped[int | None] = mapped_column(ForeignKey("agreement_templates.id"), nullable=True)
    delivery_instruction_template_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("agreement_template_versions.id"),
        nullable=True,
    )
    delivery_instruction_template_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    delivery_instruction_pdf_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    supplier_payment_voucher_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    supplier_delivery_doc_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    outbound_doc_file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    actual_outbound_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    status: Mapped[PurchaseOrderV5Status] = mapped_column(
        SQLEnum(PurchaseOrderV5Status, native_enum=False),
        nullable=False,
        default=PurchaseOrderV5Status.PENDING_SUBMIT,
        index=True,
    )
    contract_confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    contract_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier_paid_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    supplier_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier_reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    supplier_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warehouse_reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    warehouse_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InventoryBalance(Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uk_inventory_balances_wh_product"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("oil_products.id"), nullable=False, index=True)
    on_hand_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    reserved_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    available_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False, default=Decimal("0.0000"))
    last_movement_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SalesInventoryReservation(Base):
    __tablename__ = "sales_inventory_reservations"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, unique=True, index=True)
    inventory_balance_id: Mapped[int] = mapped_column(ForeignKey("inventory_balances.id"), nullable=False, index=True)
    reserved_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    status: Mapped[SalesInventoryReservationStatus] = mapped_column(
        SQLEnum(SalesInventoryReservationStatus, native_enum=False),
        nullable=False,
        default=SalesInventoryReservationStatus.ACTIVE,
        index=True,
    )
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        Index("idx_inventory_movements_wh_product_time", "warehouse_id", "product_id", "created_at"),
        Index("idx_inventory_movements_business", "business_type", "business_id"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    movement_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("oil_products.id"), nullable=False, index=True)
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        SQLEnum(InventoryMovementType, native_enum=False),
        nullable=False,
        index=True,
    )
    business_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    business_id: Mapped[int] = mapped_column(ID_TYPE, nullable=False, index=True)
    before_on_hand_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    change_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    after_on_hand_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    before_reserved_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    after_reserved_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PurchaseStockIn(Base):
    __tablename__ = "purchase_stock_ins"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    stock_in_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    purchase_contract_id: Mapped[int] = mapped_column(ForeignKey("purchase_contracts.id"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("oil_products.id"), nullable=False, index=True)
    stock_in_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    stock_in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[PurchaseStockInStatus] = mapped_column(
        SQLEnum(PurchaseStockInStatus, native_enum=False),
        nullable=False,
        default=PurchaseStockInStatus.PENDING_CONFIRM,
        index=True,
    )
    source_kind: Mapped[PurchaseStockInSourceKind] = mapped_column(
        SQLEnum(PurchaseStockInSourceKind, native_enum=False),
        nullable=False,
        default=PurchaseStockInSourceKind.PRIMARY_AUTO,
        index=True,
    )
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    adjustment_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("oil_products.id"), nullable=False, index=True)
    adjust_type: Mapped[InventoryAdjustmentType] = mapped_column(
        SQLEnum(InventoryAdjustmentType, native_enum=False),
        nullable=False,
        index=True,
    )
    before_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    adjust_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    after_qty_ton: Mapped[Decimal] = mapped_column(QTY_TYPE, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FileAsset(Base):
    __tablename__ = "file_assets"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    file_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(ID_TYPE, nullable=False)
    storage_backend: Mapped[StorageBackend] = mapped_column(
        SQLEnum(StorageBackend, native_enum=False),
        nullable=False,
        default=StorageBackend.LOCAL,
    )
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FileAssetLink(Base):
    __tablename__ = "file_asset_links"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(ID_TYPE, nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_asset_id: Mapped[int] = mapped_column(ForeignKey("file_assets.id"), nullable=False, index=True)
    sort_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    report_type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType, native_enum=False),
        nullable=False,
        index=True,
    )
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    generator_role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True, index=True)
    from_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    field_profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    file_asset_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id"), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ReportExportStatus] = mapped_column(
        SQLEnum(ReportExportStatus, native_enum=False),
        nullable=False,
        default=ReportExportStatus.GENERATED,
        index=True,
    )
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
