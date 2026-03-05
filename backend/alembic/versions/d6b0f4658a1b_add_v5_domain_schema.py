"""add v5 domain schema

Revision ID: d6b0f4658a1b
Revises: 8b7a6c5d4e3f
Create Date: 2026-03-01 19:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d6b0f4658a1b"
down_revision: str | None = "8b7a6c5d4e3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
AMOUNT_TYPE = sa.Numeric(18, 2)
QTY_TYPE = sa.Numeric(18, 4)
RATE_TYPE = sa.Numeric(5, 4)

COMPANY_TYPE_ENUM = sa.Enum(
    "CUSTOMER",
    "SUPPLIER",
    "OPERATOR",
    "PLATFORM",
    name="companytype",
    native_enum=False,
)
TEMPLATE_TYPE_ENUM = sa.Enum(
    "DELIVERY_INSTRUCTION",
    "SALES_CONTRACT",
    "PURCHASE_CONTRACT",
    name="templatetype",
    native_enum=False,
)
TEMPLATE_STATUS_ENUM = sa.Enum(
    "ENABLED",
    "DISABLED",
    name="templatestatus",
    native_enum=False,
)
CONTRACT_STATUS_ENUM = sa.Enum(
    "DRAFT",
    "PENDING_EFFECTIVE",
    "EFFECTIVE",
    "PARTIALLY_EXECUTED",
    "COMPLETED",
    "VOIDED",
    name="contractstatus",
    native_enum=False,
)
CONTRACT_KIND_ENUM = sa.Enum(
    "PRIMARY",
    "SUPPLEMENT",
    name="contractkind",
    native_enum=False,
)
SALES_ORDER_STATUS_ENUM = sa.Enum(
    "SUBMITTED",
    "OPERATOR_APPROVED",
    "CUSTOMER_PAYMENT_CONFIRMED",
    "READY_FOR_OUTBOUND",
    "COMPLETED",
    "REJECTED",
    "ABNORMAL_CLOSED",
    name="salesorderv5status",
    native_enum=False,
)
PURCHASE_ORDER_STATUS_ENUM = sa.Enum(
    "PENDING_SUBMIT",
    "SUPPLIER_PAYMENT_PENDING",
    "SUPPLIER_REVIEW_PENDING",
    "WAREHOUSE_PENDING",
    "COMPLETED",
    "ABNORMAL_CLOSED",
    name="purchaseorderv5status",
    native_enum=False,
)
PURCHASE_STOCK_IN_STATUS_ENUM = sa.Enum(
    "PENDING_CONFIRM",
    "CONFIRMED",
    "VOIDED",
    name="purchasestockinstatus",
    native_enum=False,
)
PURCHASE_STOCK_IN_SOURCE_ENUM = sa.Enum(
    "PRIMARY_AUTO",
    "SUPPLEMENT_AUTO",
    "MANUAL_APPEND",
    name="purchasestockinsourcekind",
    native_enum=False,
)
SALES_RESERVATION_STATUS_ENUM = sa.Enum(
    "ACTIVE",
    "RELEASED",
    "CONSUMED",
    name="salesinventoryreservationstatus",
    native_enum=False,
)
INVENTORY_MOVEMENT_TYPE_ENUM = sa.Enum(
    "PURCHASE_STOCK_IN",
    "PURCHASE_SUPPLEMENT_STOCK_IN",
    "SALES_RESERVE",
    "SALES_RESERVE_RELEASE",
    "SALES_OUTBOUND",
    "INVENTORY_ADJUSTMENT",
    name="inventorymovementtype",
    native_enum=False,
)
INVENTORY_ADJUSTMENT_TYPE_ENUM = sa.Enum(
    "INITIALIZE",
    "INCREASE",
    "DECREASE",
    name="inventoryadjustmenttype",
    native_enum=False,
)
STORAGE_BACKEND_ENUM = sa.Enum(
    "LOCAL",
    "OSS",
    name="storagebackend",
    native_enum=False,
)
REPORT_TYPE_ENUM = sa.Enum(
    "SALES_ORDERS",
    "PURCHASE_ORDERS",
    "SALES_CONTRACTS",
    "PURCHASE_CONTRACTS",
    "INVENTORY_MOVEMENTS",
    "WAREHOUSE_LEDGER",
    name="reporttype",
    native_enum=False,
)
REPORT_EXPORT_STATUS_ENUM = sa.Enum(
    "GENERATED",
    "FAILED",
    name="reportexportstatus",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("company_code", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=128), nullable=False),
        sa.Column("company_type", COMPANY_TYPE_ENUM, nullable=False),
        sa.Column("tax_no", sa.String(length=64), nullable=True),
        sa.Column("contact_name", sa.String(length=64), nullable=True),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_code", name="uq_companies_company_code"),
    )
    op.create_index("idx_companies_type_name", "companies", ["company_type", "company_name"], unique=False)
    op.create_index(op.f("ix_companies_company_code"), "companies", ["company_code"], unique=False)
    op.create_index(op.f("ix_companies_company_name"), "companies", ["company_name"], unique=False)
    op.create_index(op.f("ix_companies_company_type"), "companies", ["company_type"], unique=False)
    op.create_index(op.f("ix_companies_is_active"), "companies", ["is_active"], unique=False)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("company_id", ID_TYPE, nullable=True))
        batch_op.add_column(sa.Column("company_name_snapshot", sa.String(length=128), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_company_id"), ["company_id"], unique=False)
        batch_op.create_foreign_key("fk_users_company_id", "companies", ["company_id"], ["id"])

    with op.batch_alter_table("warehouses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("warehouse_code", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("company_id", ID_TYPE, nullable=True))
        batch_op.create_index(batch_op.f("ix_warehouses_warehouse_code"), ["warehouse_code"], unique=True)
        batch_op.create_index(batch_op.f("ix_warehouses_company_id"), ["company_id"], unique=False)
        batch_op.create_foreign_key("fk_warehouses_company_id", "companies", ["company_id"], ["id"])

    with op.batch_alter_table("oil_products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("product_code", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("unit_name", sa.String(length=16), nullable=False, server_default="吨"))
        batch_op.create_index(batch_op.f("ix_oil_products_product_code"), ["product_code"], unique=True)

    op.create_table(
        "file_assets",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("file_key", sa.String(length=255), nullable=False),
        sa.Column("business_type", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_backend", STORAGE_BACKEND_ENUM, nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_key", name="uq_file_assets_file_key"),
    )
    op.create_index(op.f("ix_file_assets_business_type"), "file_assets", ["business_type"], unique=False)
    op.create_index(op.f("ix_file_assets_file_key"), "file_assets", ["file_key"], unique=False)

    op.create_table(
        "agreement_templates",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("template_type", TEMPLATE_TYPE_ENUM, nullable=False),
        sa.Column("template_code", sa.String(length=64), nullable=False),
        sa.Column("template_name", sa.String(length=128), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", TEMPLATE_STATUS_ENUM, nullable=False, server_default="ENABLED"),
        sa.Column("current_version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_code", name="uq_agreement_templates_template_code"),
    )
    op.create_index(
        "idx_agreement_templates_type_status_default",
        "agreement_templates",
        ["template_type", "status", "is_default"],
        unique=False,
    )
    op.create_index(op.f("ix_agreement_templates_template_code"), "agreement_templates", ["template_code"], unique=False)
    op.create_index(op.f("ix_agreement_templates_template_type"), "agreement_templates", ["template_type"], unique=False)
    op.create_index(op.f("ix_agreement_templates_is_default"), "agreement_templates", ["is_default"], unique=False)
    op.create_index(op.f("ix_agreement_templates_status"), "agreement_templates", ["status"], unique=False)

    op.create_table(
        "agreement_template_versions",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("template_id", ID_TYPE, nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("template_title", sa.String(length=128), nullable=True),
        sa.Column("template_content_json", sa.JSON(), nullable=False),
        sa.Column("placeholder_schema_json", sa.JSON(), nullable=False),
        sa.Column("render_config_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["agreement_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "version_no", name="uk_agreement_template_versions_template_version"),
    )
    op.create_index(op.f("ix_agreement_template_versions_template_id"), "agreement_template_versions", ["template_id"], unique=False)

    op.create_table(
        "sales_contracts",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("contract_no", sa.String(length=64), nullable=False),
        sa.Column("contract_kind", CONTRACT_KIND_ENUM, nullable=False, server_default="PRIMARY"),
        sa.Column("source_contract_id", ID_TYPE, nullable=True),
        sa.Column("customer_company_id", ID_TYPE, nullable=False),
        sa.Column("template_id", ID_TYPE, nullable=False),
        sa.Column("template_version_id", ID_TYPE, nullable=False),
        sa.Column("template_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("variable_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("signed_contract_file_id", ID_TYPE, nullable=True),
        sa.Column("deposit_receipt_file_id", ID_TYPE, nullable=True),
        sa.Column("contract_date", sa.Date(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_by", sa.Integer(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by", sa.Integer(), nullable=True),
        sa.Column("status", CONTRACT_STATUS_ENUM, nullable=False, server_default="DRAFT"),
        sa.Column("deposit_rate", RATE_TYPE, nullable=False, server_default="0.1000"),
        sa.Column("deposit_amount", AMOUNT_TYPE, nullable=False, server_default="0.00"),
        sa.Column("base_contract_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("supplement_qty_total", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("effective_contract_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("executed_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("pending_execution_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("over_executed_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["customer_company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["deposit_receipt_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["effective_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["signed_contract_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["source_contract_id"], ["sales_contracts.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["agreement_templates.id"]),
        sa.ForeignKeyConstraint(["template_version_id"], ["agreement_template_versions.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["voided_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_no", name="uq_sales_contracts_contract_no"),
    )
    op.create_index(op.f("ix_sales_contracts_contract_no"), "sales_contracts", ["contract_no"], unique=False)
    op.create_index(op.f("ix_sales_contracts_contract_kind"), "sales_contracts", ["contract_kind"], unique=False)
    op.create_index(op.f("ix_sales_contracts_customer_company_id"), "sales_contracts", ["customer_company_id"], unique=False)
    op.create_index(op.f("ix_sales_contracts_status"), "sales_contracts", ["status"], unique=False)
    op.create_index(op.f("ix_sales_contracts_contract_date"), "sales_contracts", ["contract_date"], unique=False)
    op.create_index(op.f("ix_sales_contracts_source_contract_id"), "sales_contracts", ["source_contract_id"], unique=False)

    op.create_table(
        "sales_contract_items",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("sales_contract_id", ID_TYPE, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("qty_ton", QTY_TYPE, nullable=False),
        sa.Column("unit_name", sa.String(length=16), nullable=False, server_default="吨"),
        sa.Column("tax_rate", RATE_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("unit_price_tax_included", AMOUNT_TYPE, nullable=False),
        sa.Column("amount_tax_included", AMOUNT_TYPE, nullable=False),
        sa.Column("amount_tax_excluded", AMOUNT_TYPE, nullable=False),
        sa.Column("tax_amount", AMOUNT_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["oil_products.id"]),
        sa.ForeignKeyConstraint(["sales_contract_id"], ["sales_contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sales_contract_id", "product_id", name="uk_sales_contract_items_contract_product"),
    )
    op.create_index(op.f("ix_sales_contract_items_sales_contract_id"), "sales_contract_items", ["sales_contract_id"], unique=False)
    op.create_index(op.f("ix_sales_contract_items_product_id"), "sales_contract_items", ["product_id"], unique=False)

    op.create_table(
        "purchase_contracts",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("contract_no", sa.String(length=64), nullable=False),
        sa.Column("contract_kind", CONTRACT_KIND_ENUM, nullable=False, server_default="PRIMARY"),
        sa.Column("source_contract_id", ID_TYPE, nullable=True),
        sa.Column("supplier_company_id", ID_TYPE, nullable=False),
        sa.Column("template_id", ID_TYPE, nullable=False),
        sa.Column("template_version_id", ID_TYPE, nullable=False),
        sa.Column("template_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("variable_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("signed_contract_file_id", ID_TYPE, nullable=True),
        sa.Column("deposit_receipt_file_id", ID_TYPE, nullable=True),
        sa.Column("contract_date", sa.Date(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_by", sa.Integer(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by", sa.Integer(), nullable=True),
        sa.Column("status", CONTRACT_STATUS_ENUM, nullable=False, server_default="DRAFT"),
        sa.Column("deposit_rate", RATE_TYPE, nullable=False, server_default="0.1000"),
        sa.Column("deposit_amount", AMOUNT_TYPE, nullable=False, server_default="0.00"),
        sa.Column("base_contract_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("supplement_qty_total", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("effective_contract_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("executed_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("pending_execution_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("over_executed_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("stocked_in_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("pending_stock_in_qty", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["deposit_receipt_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["effective_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["signed_contract_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["source_contract_id"], ["purchase_contracts.id"]),
        sa.ForeignKeyConstraint(["supplier_company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["agreement_templates.id"]),
        sa.ForeignKeyConstraint(["template_version_id"], ["agreement_template_versions.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["voided_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_no", name="uq_purchase_contracts_contract_no"),
    )
    op.create_index(op.f("ix_purchase_contracts_contract_no"), "purchase_contracts", ["contract_no"], unique=False)
    op.create_index(op.f("ix_purchase_contracts_contract_kind"), "purchase_contracts", ["contract_kind"], unique=False)
    op.create_index(op.f("ix_purchase_contracts_supplier_company_id"), "purchase_contracts", ["supplier_company_id"], unique=False)
    op.create_index(op.f("ix_purchase_contracts_status"), "purchase_contracts", ["status"], unique=False)
    op.create_index(op.f("ix_purchase_contracts_contract_date"), "purchase_contracts", ["contract_date"], unique=False)
    op.create_index(op.f("ix_purchase_contracts_source_contract_id"), "purchase_contracts", ["source_contract_id"], unique=False)

    op.create_table(
        "purchase_contract_items",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("purchase_contract_id", ID_TYPE, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("qty_ton", QTY_TYPE, nullable=False),
        sa.Column("unit_name", sa.String(length=16), nullable=False, server_default="吨"),
        sa.Column("tax_rate", RATE_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("unit_price_tax_included", AMOUNT_TYPE, nullable=False),
        sa.Column("amount_tax_included", AMOUNT_TYPE, nullable=False),
        sa.Column("amount_tax_excluded", AMOUNT_TYPE, nullable=False),
        sa.Column("tax_amount", AMOUNT_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["oil_products.id"]),
        sa.ForeignKeyConstraint(["purchase_contract_id"], ["purchase_contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_contract_id", "product_id", name="uk_purchase_contract_items_contract_product"),
    )
    op.create_index(op.f("ix_purchase_contract_items_purchase_contract_id"), "purchase_contract_items", ["purchase_contract_id"], unique=False)
    op.create_index(op.f("ix_purchase_contract_items_product_id"), "purchase_contract_items", ["product_id"], unique=False)

    op.create_table(
        "contract_execution_logs",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("contract_type", sa.String(length=32), nullable=False),
        sa.Column("contract_id", ID_TYPE, nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", ID_TYPE, nullable=False),
        sa.Column("qty_ton", QTY_TYPE, nullable=False),
        sa.Column("before_executed_qty", QTY_TYPE, nullable=False),
        sa.Column("after_executed_qty", QTY_TYPE, nullable=False),
        sa.Column("before_pending_qty", QTY_TYPE, nullable=False),
        sa.Column("after_pending_qty", QTY_TYPE, nullable=False),
        sa.Column("operator_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contract_execution_logs_contract_type"), "contract_execution_logs", ["contract_type"], unique=False)
    op.create_index(op.f("ix_contract_execution_logs_contract_id"), "contract_execution_logs", ["contract_id"], unique=False)
    op.create_index(op.f("ix_contract_execution_logs_source_type"), "contract_execution_logs", ["source_type"], unique=False)
    op.create_index(op.f("ix_contract_execution_logs_source_id"), "contract_execution_logs", ["source_id"], unique=False)
    op.create_index(op.f("ix_contract_execution_logs_operator_user_id"), "contract_execution_logs", ["operator_user_id"], unique=False)

    op.create_table(
        "customer_transport_profiles",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("customer_company_id", ID_TYPE, nullable=False),
        sa.Column("transport_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["customer_company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_customer_transport_profiles_customer_last_used",
        "customer_transport_profiles",
        ["customer_company_id", "last_used_at"],
        unique=False,
    )
    op.create_index(op.f("ix_customer_transport_profiles_is_default"), "customer_transport_profiles", ["is_default"], unique=False)

    op.create_table(
        "sales_orders",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("sales_order_no", sa.String(length=64), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("customer_company_id", ID_TYPE, nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sales_contract_id", ID_TYPE, nullable=False),
        sa.Column("sales_contract_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("qty_ton", QTY_TYPE, nullable=False),
        sa.Column("unit_price_tax_included", AMOUNT_TYPE, nullable=False),
        sa.Column("amount_tax_included", AMOUNT_TYPE, nullable=False),
        sa.Column("operator_company_id", ID_TYPE, nullable=True),
        sa.Column("operator_company_name_snapshot", sa.String(length=128), nullable=True),
        sa.Column("transport_profile_id", ID_TYPE, nullable=True),
        sa.Column("transport_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("received_amount", AMOUNT_TYPE, nullable=True),
        sa.Column("customer_payment_receipt_file_id", ID_TYPE, nullable=True),
        sa.Column("reserved_qty_ton", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("actual_outbound_qty_ton", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("status", SALES_ORDER_STATUS_ENUM, nullable=False, server_default="SUBMITTED"),
        sa.Column("operator_reviewed_by", sa.Integer(), nullable=True),
        sa.Column("operator_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finance_reviewed_by", sa.Integer(), nullable=True),
        sa.Column("finance_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_reason", sa.String(length=255), nullable=True),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["customer_company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["customer_payment_receipt_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["finance_reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["operator_company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["operator_reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["oil_products.id"]),
        sa.ForeignKeyConstraint(["sales_contract_id"], ["sales_contracts.id"]),
        sa.ForeignKeyConstraint(["transport_profile_id"], ["customer_transport_profiles.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sales_order_no", name="uq_sales_orders_sales_order_no"),
    )
    op.create_index("idx_sales_orders_customer_status_date", "sales_orders", ["customer_company_id", "status", "order_date"], unique=False)
    op.create_index(op.f("ix_sales_orders_sales_order_no"), "sales_orders", ["sales_order_no"], unique=False)
    op.create_index(op.f("ix_sales_orders_order_date"), "sales_orders", ["order_date"], unique=False)
    op.create_index(op.f("ix_sales_orders_customer_company_id"), "sales_orders", ["customer_company_id"], unique=False)
    op.create_index(op.f("ix_sales_orders_warehouse_id"), "sales_orders", ["warehouse_id"], unique=False)
    op.create_index(op.f("ix_sales_orders_product_id"), "sales_orders", ["product_id"], unique=False)
    op.create_index(op.f("ix_sales_orders_sales_contract_id"), "sales_orders", ["sales_contract_id"], unique=False)
    op.create_index(op.f("ix_sales_orders_status"), "sales_orders", ["status"], unique=False)

    op.create_table(
        "purchase_orders",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("purchase_order_no", sa.String(length=64), nullable=False),
        sa.Column("sales_order_id", ID_TYPE, nullable=False),
        sa.Column("purchase_contract_id", ID_TYPE, nullable=True),
        sa.Column("purchase_contract_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("supplier_company_id", ID_TYPE, nullable=True),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("qty_ton", QTY_TYPE, nullable=False),
        sa.Column("unit_price_tax_included", AMOUNT_TYPE, nullable=True),
        sa.Column("amount_tax_included", AMOUNT_TYPE, nullable=True),
        sa.Column("confirm_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("confirm_acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delivery_instruction_template_id", ID_TYPE, nullable=True),
        sa.Column("delivery_instruction_template_version_id", ID_TYPE, nullable=True),
        sa.Column("delivery_instruction_template_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("delivery_instruction_pdf_file_id", ID_TYPE, nullable=True),
        sa.Column("supplier_payment_voucher_file_id", ID_TYPE, nullable=True),
        sa.Column("supplier_delivery_doc_file_id", ID_TYPE, nullable=True),
        sa.Column("outbound_doc_file_id", ID_TYPE, nullable=True),
        sa.Column("actual_outbound_qty_ton", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("status", PURCHASE_ORDER_STATUS_ENUM, nullable=False, server_default="PENDING_SUBMIT"),
        sa.Column("contract_confirmed_by", sa.Integer(), nullable=True),
        sa.Column("contract_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supplier_paid_by", sa.Integer(), nullable=True),
        sa.Column("supplier_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supplier_reviewed_by", sa.Integer(), nullable=True),
        sa.Column("supplier_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("warehouse_reviewed_by", sa.Integer(), nullable=True),
        sa.Column("warehouse_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_reason", sa.String(length=255), nullable=True),
        sa.Column("closed_by", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["contract_confirmed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["delivery_instruction_pdf_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["delivery_instruction_template_id"], ["agreement_templates.id"]),
        sa.ForeignKeyConstraint(["delivery_instruction_template_version_id"], ["agreement_template_versions.id"]),
        sa.ForeignKeyConstraint(["outbound_doc_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["oil_products.id"]),
        sa.ForeignKeyConstraint(["purchase_contract_id"], ["purchase_contracts.id"]),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"]),
        sa.ForeignKeyConstraint(["supplier_company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["supplier_delivery_doc_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["supplier_paid_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["supplier_payment_voucher_file_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["supplier_reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["warehouse_reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_order_no", name="uq_purchase_orders_purchase_order_no"),
        sa.UniqueConstraint("sales_order_id", name="uk_purchase_orders_sales_order_id"),
    )
    op.create_index(
        "idx_purchase_orders_status_supplier_warehouse",
        "purchase_orders",
        ["status", "supplier_company_id", "warehouse_id"],
        unique=False,
    )
    op.create_index(op.f("ix_purchase_orders_purchase_order_no"), "purchase_orders", ["purchase_order_no"], unique=False)
    op.create_index(op.f("ix_purchase_orders_sales_order_id"), "purchase_orders", ["sales_order_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_purchase_contract_id"), "purchase_orders", ["purchase_contract_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_supplier_company_id"), "purchase_orders", ["supplier_company_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_warehouse_id"), "purchase_orders", ["warehouse_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_product_id"), "purchase_orders", ["product_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_status"), "purchase_orders", ["status"], unique=False)

    op.create_table(
        "inventory_balances",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("on_hand_qty_ton", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("reserved_qty_ton", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("available_qty_ton", QTY_TYPE, nullable=False, server_default="0.0000"),
        sa.Column("last_movement_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["product_id"], ["oil_products.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("warehouse_id", "product_id", name="uk_inventory_balances_wh_product"),
    )
    op.create_index(op.f("ix_inventory_balances_warehouse_id"), "inventory_balances", ["warehouse_id"], unique=False)
    op.create_index(op.f("ix_inventory_balances_product_id"), "inventory_balances", ["product_id"], unique=False)

    op.create_table(
        "sales_inventory_reservations",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("sales_order_id", ID_TYPE, nullable=False),
        sa.Column("inventory_balance_id", ID_TYPE, nullable=False),
        sa.Column("reserved_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("status", SALES_RESERVATION_STATUS_ENUM, nullable=False, server_default="ACTIVE"),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["inventory_balance_id"], ["inventory_balances.id"]),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sales_order_id", name="uk_sales_inventory_reservations_sales_order_id"),
    )
    op.create_index(op.f("ix_sales_inventory_reservations_sales_order_id"), "sales_inventory_reservations", ["sales_order_id"], unique=False)
    op.create_index(op.f("ix_sales_inventory_reservations_inventory_balance_id"), "sales_inventory_reservations", ["inventory_balance_id"], unique=False)
    op.create_index(op.f("ix_sales_inventory_reservations_status"), "sales_inventory_reservations", ["status"], unique=False)

    op.create_table(
        "inventory_movements",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("movement_no", sa.String(length=64), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", INVENTORY_MOVEMENT_TYPE_ENUM, nullable=False),
        sa.Column("business_type", sa.String(length=32), nullable=False),
        sa.Column("business_id", ID_TYPE, nullable=False),
        sa.Column("before_on_hand_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("change_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("after_on_hand_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("before_reserved_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("after_reserved_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("operator_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["oil_products.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("movement_no", name="uq_inventory_movements_movement_no"),
    )
    op.create_index("idx_inventory_movements_wh_product_time", "inventory_movements", ["warehouse_id", "product_id", "created_at"], unique=False)
    op.create_index("idx_inventory_movements_business", "inventory_movements", ["business_type", "business_id"], unique=False)
    op.create_index(op.f("ix_inventory_movements_movement_no"), "inventory_movements", ["movement_no"], unique=False)
    op.create_index(op.f("ix_inventory_movements_movement_type"), "inventory_movements", ["movement_type"], unique=False)

    op.create_table(
        "purchase_stock_ins",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("stock_in_no", sa.String(length=64), nullable=False),
        sa.Column("purchase_contract_id", ID_TYPE, nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("stock_in_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("stock_in_date", sa.Date(), nullable=True),
        sa.Column("status", PURCHASE_STOCK_IN_STATUS_ENUM, nullable=False, server_default="PENDING_CONFIRM"),
        sa.Column("source_kind", PURCHASE_STOCK_IN_SOURCE_ENUM, nullable=False, server_default="PRIMARY_AUTO"),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["oil_products.id"]),
        sa.ForeignKeyConstraint(["purchase_contract_id"], ["purchase_contracts.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_in_no", name="uq_purchase_stock_ins_stock_in_no"),
    )
    op.create_index(op.f("ix_purchase_stock_ins_stock_in_no"), "purchase_stock_ins", ["stock_in_no"], unique=False)
    op.create_index(op.f("ix_purchase_stock_ins_purchase_contract_id"), "purchase_stock_ins", ["purchase_contract_id"], unique=False)
    op.create_index(op.f("ix_purchase_stock_ins_warehouse_id"), "purchase_stock_ins", ["warehouse_id"], unique=False)
    op.create_index(op.f("ix_purchase_stock_ins_product_id"), "purchase_stock_ins", ["product_id"], unique=False)
    op.create_index(op.f("ix_purchase_stock_ins_status"), "purchase_stock_ins", ["status"], unique=False)
    op.create_index(op.f("ix_purchase_stock_ins_source_kind"), "purchase_stock_ins", ["source_kind"], unique=False)

    op.create_table(
        "inventory_adjustments",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("adjustment_no", sa.String(length=64), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("adjust_type", INVENTORY_ADJUSTMENT_TYPE_ENUM, nullable=False),
        sa.Column("before_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("adjust_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("after_qty_ton", QTY_TYPE, nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["oil_products.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adjustment_no", name="uq_inventory_adjustments_adjustment_no"),
    )
    op.create_index(op.f("ix_inventory_adjustments_adjustment_no"), "inventory_adjustments", ["adjustment_no"], unique=False)
    op.create_index(op.f("ix_inventory_adjustments_warehouse_id"), "inventory_adjustments", ["warehouse_id"], unique=False)
    op.create_index(op.f("ix_inventory_adjustments_product_id"), "inventory_adjustments", ["product_id"], unique=False)
    op.create_index(op.f("ix_inventory_adjustments_adjust_type"), "inventory_adjustments", ["adjust_type"], unique=False)

    op.create_table(
        "file_asset_links",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", ID_TYPE, nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("file_asset_id", ID_TYPE, nullable=False),
        sa.Column("sort_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["file_asset_id"], ["file_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_asset_links_entity_type"), "file_asset_links", ["entity_type"], unique=False)
    op.create_index(op.f("ix_file_asset_links_entity_id"), "file_asset_links", ["entity_id"], unique=False)
    op.create_index(op.f("ix_file_asset_links_field_name"), "file_asset_links", ["field_name"], unique=False)
    op.create_index(op.f("ix_file_asset_links_file_asset_id"), "file_asset_links", ["file_asset_id"], unique=False)

    op.create_table(
        "report_exports",
        sa.Column("id", ID_TYPE, autoincrement=True, nullable=False),
        sa.Column("report_type", REPORT_TYPE_ENUM, nullable=False),
        sa.Column("generated_by", sa.Integer(), nullable=False),
        sa.Column("generator_role", sa.String(length=32), nullable=False),
        sa.Column("scope_company_id", ID_TYPE, nullable=True),
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
        sa.Column("from_date", sa.Date(), nullable=True),
        sa.Column("to_date", sa.Date(), nullable=True),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("field_profile_json", sa.JSON(), nullable=False),
        sa.Column("file_asset_id", ID_TYPE, nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", REPORT_EXPORT_STATUS_ENUM, nullable=False, server_default="GENERATED"),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["file_asset_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["scope_company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_exports_report_type"), "report_exports", ["report_type"], unique=False)
    op.create_index(op.f("ix_report_exports_generated_by"), "report_exports", ["generated_by"], unique=False)
    op.create_index(op.f("ix_report_exports_generator_role"), "report_exports", ["generator_role"], unique=False)
    op.create_index(op.f("ix_report_exports_scope_company_id"), "report_exports", ["scope_company_id"], unique=False)
    op.create_index(op.f("ix_report_exports_warehouse_id"), "report_exports", ["warehouse_id"], unique=False)
    op.create_index(op.f("ix_report_exports_status"), "report_exports", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_exports_status"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_warehouse_id"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_scope_company_id"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_generator_role"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_generated_by"), table_name="report_exports")
    op.drop_index(op.f("ix_report_exports_report_type"), table_name="report_exports")
    op.drop_table("report_exports")

    op.drop_index(op.f("ix_file_asset_links_file_asset_id"), table_name="file_asset_links")
    op.drop_index(op.f("ix_file_asset_links_field_name"), table_name="file_asset_links")
    op.drop_index(op.f("ix_file_asset_links_entity_id"), table_name="file_asset_links")
    op.drop_index(op.f("ix_file_asset_links_entity_type"), table_name="file_asset_links")
    op.drop_table("file_asset_links")

    op.drop_index(op.f("ix_inventory_adjustments_adjust_type"), table_name="inventory_adjustments")
    op.drop_index(op.f("ix_inventory_adjustments_product_id"), table_name="inventory_adjustments")
    op.drop_index(op.f("ix_inventory_adjustments_warehouse_id"), table_name="inventory_adjustments")
    op.drop_index(op.f("ix_inventory_adjustments_adjustment_no"), table_name="inventory_adjustments")
    op.drop_table("inventory_adjustments")

    op.drop_index(op.f("ix_purchase_stock_ins_source_kind"), table_name="purchase_stock_ins")
    op.drop_index(op.f("ix_purchase_stock_ins_status"), table_name="purchase_stock_ins")
    op.drop_index(op.f("ix_purchase_stock_ins_product_id"), table_name="purchase_stock_ins")
    op.drop_index(op.f("ix_purchase_stock_ins_warehouse_id"), table_name="purchase_stock_ins")
    op.drop_index(op.f("ix_purchase_stock_ins_purchase_contract_id"), table_name="purchase_stock_ins")
    op.drop_index(op.f("ix_purchase_stock_ins_stock_in_no"), table_name="purchase_stock_ins")
    op.drop_table("purchase_stock_ins")

    op.drop_index(op.f("ix_inventory_movements_movement_type"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_movement_no"), table_name="inventory_movements")
    op.drop_index("idx_inventory_movements_business", table_name="inventory_movements")
    op.drop_index("idx_inventory_movements_wh_product_time", table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index(op.f("ix_sales_inventory_reservations_status"), table_name="sales_inventory_reservations")
    op.drop_index(op.f("ix_sales_inventory_reservations_inventory_balance_id"), table_name="sales_inventory_reservations")
    op.drop_index(op.f("ix_sales_inventory_reservations_sales_order_id"), table_name="sales_inventory_reservations")
    op.drop_table("sales_inventory_reservations")

    op.drop_index(op.f("ix_inventory_balances_product_id"), table_name="inventory_balances")
    op.drop_index(op.f("ix_inventory_balances_warehouse_id"), table_name="inventory_balances")
    op.drop_table("inventory_balances")

    op.drop_index(op.f("ix_purchase_orders_status"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_product_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_warehouse_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_supplier_company_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_purchase_contract_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_sales_order_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_purchase_order_no"), table_name="purchase_orders")
    op.drop_index("idx_purchase_orders_status_supplier_warehouse", table_name="purchase_orders")
    op.drop_table("purchase_orders")

    op.drop_index(op.f("ix_sales_orders_status"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_sales_contract_id"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_product_id"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_warehouse_id"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_customer_company_id"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_order_date"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_sales_order_no"), table_name="sales_orders")
    op.drop_index("idx_sales_orders_customer_status_date", table_name="sales_orders")
    op.drop_table("sales_orders")

    op.drop_index(op.f("ix_customer_transport_profiles_is_default"), table_name="customer_transport_profiles")
    op.drop_index("idx_customer_transport_profiles_customer_last_used", table_name="customer_transport_profiles")
    op.drop_table("customer_transport_profiles")

    op.drop_index(op.f("ix_contract_execution_logs_operator_user_id"), table_name="contract_execution_logs")
    op.drop_index(op.f("ix_contract_execution_logs_source_id"), table_name="contract_execution_logs")
    op.drop_index(op.f("ix_contract_execution_logs_source_type"), table_name="contract_execution_logs")
    op.drop_index(op.f("ix_contract_execution_logs_contract_id"), table_name="contract_execution_logs")
    op.drop_index(op.f("ix_contract_execution_logs_contract_type"), table_name="contract_execution_logs")
    op.drop_table("contract_execution_logs")

    op.drop_index(op.f("ix_purchase_contract_items_product_id"), table_name="purchase_contract_items")
    op.drop_index(op.f("ix_purchase_contract_items_purchase_contract_id"), table_name="purchase_contract_items")
    op.drop_table("purchase_contract_items")

    op.drop_index(op.f("ix_purchase_contracts_source_contract_id"), table_name="purchase_contracts")
    op.drop_index(op.f("ix_purchase_contracts_contract_date"), table_name="purchase_contracts")
    op.drop_index(op.f("ix_purchase_contracts_status"), table_name="purchase_contracts")
    op.drop_index(op.f("ix_purchase_contracts_supplier_company_id"), table_name="purchase_contracts")
    op.drop_index(op.f("ix_purchase_contracts_contract_kind"), table_name="purchase_contracts")
    op.drop_index(op.f("ix_purchase_contracts_contract_no"), table_name="purchase_contracts")
    op.drop_table("purchase_contracts")

    op.drop_index(op.f("ix_sales_contract_items_product_id"), table_name="sales_contract_items")
    op.drop_index(op.f("ix_sales_contract_items_sales_contract_id"), table_name="sales_contract_items")
    op.drop_table("sales_contract_items")

    op.drop_index(op.f("ix_sales_contracts_source_contract_id"), table_name="sales_contracts")
    op.drop_index(op.f("ix_sales_contracts_contract_date"), table_name="sales_contracts")
    op.drop_index(op.f("ix_sales_contracts_status"), table_name="sales_contracts")
    op.drop_index(op.f("ix_sales_contracts_customer_company_id"), table_name="sales_contracts")
    op.drop_index(op.f("ix_sales_contracts_contract_kind"), table_name="sales_contracts")
    op.drop_index(op.f("ix_sales_contracts_contract_no"), table_name="sales_contracts")
    op.drop_table("sales_contracts")

    op.drop_index(op.f("ix_agreement_template_versions_template_id"), table_name="agreement_template_versions")
    op.drop_table("agreement_template_versions")

    op.drop_index(op.f("ix_agreement_templates_status"), table_name="agreement_templates")
    op.drop_index(op.f("ix_agreement_templates_is_default"), table_name="agreement_templates")
    op.drop_index(op.f("ix_agreement_templates_template_type"), table_name="agreement_templates")
    op.drop_index(op.f("ix_agreement_templates_template_code"), table_name="agreement_templates")
    op.drop_index("idx_agreement_templates_type_status_default", table_name="agreement_templates")
    op.drop_table("agreement_templates")

    op.drop_index(op.f("ix_file_assets_file_key"), table_name="file_assets")
    op.drop_index(op.f("ix_file_assets_business_type"), table_name="file_assets")
    op.drop_table("file_assets")

    with op.batch_alter_table("oil_products", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_oil_products_product_code"))
        batch_op.drop_column("unit_name")
        batch_op.drop_column("product_code")

    with op.batch_alter_table("warehouses", schema=None) as batch_op:
        batch_op.drop_constraint("fk_warehouses_company_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_warehouses_company_id"))
        batch_op.drop_index(batch_op.f("ix_warehouses_warehouse_code"))
        batch_op.drop_column("company_id")
        batch_op.drop_column("warehouse_code")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_company_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_users_company_id"))
        batch_op.drop_column("company_name_snapshot")
        batch_op.drop_column("company_id")

    op.drop_index(op.f("ix_companies_is_active"), table_name="companies")
    op.drop_index(op.f("ix_companies_company_type"), table_name="companies")
    op.drop_index(op.f("ix_companies_company_name"), table_name="companies")
    op.drop_index(op.f("ix_companies_company_code"), table_name="companies")
    op.drop_index("idx_companies_type_name", table_name="companies")
    op.drop_table("companies")
