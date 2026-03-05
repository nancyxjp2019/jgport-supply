from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Select, case, select
from sqlalchemy.orm import Session

from app.models.master_data import OilProduct, Warehouse
from app.models.user import User
from app.models.v5_domain import (
    AgreementTemplate,
    Company,
    ContractStatus,
    CustomerTransportProfile,
    InventoryBalance,
    PurchaseContract,
    PurchaseContractItem,
    SalesOrderV5,
    SalesContract,
    SalesContractItem,
    TemplateStatus,
    TemplateType,
)
from app.schemas.v5_reference import (
    AgreementTemplateSelectOptionOut,
    ProductSelectOptionOut,
    PurchaseContractSelectOptionOut,
    SalesContractSelectOptionOut,
    SalesOrderCreateMetaOut,
    SalesOrderCreateWarehouseProductStockOut,
    TransportProfileHistoryItemOut,
    WarehouseSelectOptionOut,
)


_ACTIVE_CONTRACT_STATUSES = (
    ContractStatus.EFFECTIVE,
    ContractStatus.PARTIALLY_EXECUTED,
)


def _normalize_template_type(raw_template_type: str | None) -> TemplateType | None:
    if raw_template_type is None:
        return None
    normalized = raw_template_type.strip().replace("-", "_").upper()
    if not normalized:
        return None
    try:
        return TemplateType[normalized]
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="template_type_invalid") from exc


def _normalize_decimal_qty(raw_qty: float | None) -> Decimal:
    if raw_qty is None:
        return Decimal("0")
    return Decimal(str(raw_qty))


def _resolve_customer_company_id(current_user: User) -> int:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer_company_not_bound")
    return current_user.company_id


def list_template_select_options(db: Session, raw_template_type: str | None) -> list[AgreementTemplateSelectOptionOut]:
    template_type = _normalize_template_type(raw_template_type)
    query: Select[tuple[AgreementTemplate]] = select(AgreementTemplate).where(AgreementTemplate.status == TemplateStatus.ENABLED)
    if template_type is not None:
        query = query.where(AgreementTemplate.template_type == template_type)
    rows = db.scalars(
        query.order_by(
            AgreementTemplate.is_default.desc(),
            AgreementTemplate.template_name.asc(),
            AgreementTemplate.id.asc(),
        )
    ).all()
    return [AgreementTemplateSelectOptionOut.model_validate(item) for item in rows]


def list_transport_history(db: Session, current_user: User) -> list[TransportProfileHistoryItemOut]:
    customer_company_id = _resolve_customer_company_id(current_user)
    rows = db.scalars(
        select(CustomerTransportProfile)
        .where(CustomerTransportProfile.customer_company_id == customer_company_id)
        .order_by(
            CustomerTransportProfile.is_default.desc(),
            case((CustomerTransportProfile.last_used_at.is_(None), 1), else_=0).asc(),
            CustomerTransportProfile.last_used_at.desc(),
            CustomerTransportProfile.id.desc(),
        )
    ).all()
    return [
        TransportProfileHistoryItemOut(
            id=item.id,
            is_default=item.is_default,
            last_used_at=item.last_used_at,
            transport_snapshot=item.transport_snapshot_json,
        )
        for item in rows
    ]


def delete_transport_history_item(db: Session, profile_id: int, current_user: User) -> None:
    customer_company_id = _resolve_customer_company_id(current_user)
    profile = db.scalar(
        select(CustomerTransportProfile).where(
            CustomerTransportProfile.id == profile_id,
            CustomerTransportProfile.customer_company_id == customer_company_id,
        )
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="transport_profile_not_found")

    linked_orders = db.scalars(
        select(SalesOrderV5).where(SalesOrderV5.transport_profile_id == profile.id)
    ).all()
    for order in linked_orders:
        order.transport_profile_id = None

    replacement_profile = None
    if profile.is_default:
        replacement_profile = db.scalar(
            select(CustomerTransportProfile)
            .where(
                CustomerTransportProfile.customer_company_id == customer_company_id,
                CustomerTransportProfile.id != profile.id,
            )
            .order_by(
                case((CustomerTransportProfile.last_used_at.is_(None), 1), else_=0).asc(),
                CustomerTransportProfile.last_used_at.desc(),
                CustomerTransportProfile.id.desc(),
            )
        )
    db.delete(profile)

    if replacement_profile is not None:
        replacement_profile.is_default = True


def list_sales_contract_select_options(
    db: Session,
    current_user: User,
    qty: float | None = None,
) -> list[SalesContractSelectOptionOut]:
    customer_company_id = _resolve_customer_company_id(current_user)
    requested_qty = _normalize_decimal_qty(qty)
    rows = db.execute(
        select(
            SalesContract.id.label("sales_contract_id"),
            SalesContract.contract_no.label("contract_no"),
            SalesContract.customer_company_id.label("customer_company_id"),
            Company.company_name.label("customer_company_name"),
            SalesContract.pending_execution_qty.label("pending_execution_qty"),
            SalesContractItem.product_id.label("product_id"),
            OilProduct.name.label("product_name"),
            SalesContractItem.unit_name.label("unit_name"),
        )
        .join(Company, Company.id == SalesContract.customer_company_id)
        .join(SalesContractItem, SalesContractItem.sales_contract_id == SalesContract.id)
        .join(OilProduct, OilProduct.id == SalesContractItem.product_id)
        .where(
            SalesContract.customer_company_id == customer_company_id,
            SalesContract.status.in_(_ACTIVE_CONTRACT_STATUSES),
            SalesContract.pending_execution_qty > Decimal("0"),
            Company.is_active.is_(True),
            OilProduct.is_active.is_(True),
        )
        .order_by(SalesContract.contract_no.asc(), SalesContractItem.id.asc())
    ).all()

    options: list[SalesContractSelectOptionOut] = []
    for row in rows:
        pending_qty = row.pending_execution_qty or Decimal("0")
        projected_pending_qty = pending_qty - requested_qty
        options.append(
            SalesContractSelectOptionOut(
                sales_contract_id=row.sales_contract_id,
                contract_no=row.contract_no,
                customer_company_id=row.customer_company_id,
                customer_company_name=row.customer_company_name,
                product_id=row.product_id,
                product_name=row.product_name,
                unit_name=row.unit_name,
                pending_execution_qty_ton=float(pending_qty),
                projected_pending_execution_qty_ton=float(max(projected_pending_qty, Decimal("0"))),
                projected_over_execution_qty_ton=float(max(-projected_pending_qty, Decimal("0"))),
            )
        )
    return options


def list_purchase_contract_select_options(
    db: Session,
    product_id: int,
    warehouse_id: int,
    qty: float,
) -> list[PurchaseContractSelectOptionOut]:
    warehouse = db.scalar(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.is_active.is_(True)))
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="warehouse_not_found")

    requested_qty = _normalize_decimal_qty(qty)
    rows = db.execute(
        select(
            PurchaseContract.id.label("purchase_contract_id"),
            PurchaseContract.contract_no.label("contract_no"),
            PurchaseContract.supplier_company_id.label("supplier_company_id"),
            Company.company_name.label("supplier_company_name"),
            PurchaseContract.pending_execution_qty.label("pending_execution_qty"),
            PurchaseContract.effective_at.label("effective_at"),
            PurchaseContractItem.product_id.label("product_id"),
            OilProduct.name.label("product_name"),
            PurchaseContractItem.unit_name.label("unit_name"),
        )
        .join(Company, Company.id == PurchaseContract.supplier_company_id)
        .join(PurchaseContractItem, PurchaseContractItem.purchase_contract_id == PurchaseContract.id)
        .join(OilProduct, OilProduct.id == PurchaseContractItem.product_id)
        .where(
            PurchaseContractItem.product_id == product_id,
            PurchaseContract.status.in_(_ACTIVE_CONTRACT_STATUSES),
            PurchaseContract.pending_execution_qty > Decimal("0"),
            Company.is_active.is_(True),
            OilProduct.is_active.is_(True),
        )
        .order_by(
            PurchaseContract.pending_execution_qty.asc(),
            case((PurchaseContract.effective_at.is_(None), 1), else_=0).asc(),
            PurchaseContract.effective_at.asc(),
            PurchaseContract.contract_no.asc(),
        )
    ).all()

    options: list[PurchaseContractSelectOptionOut] = []
    for index, row in enumerate(rows, start=1):
        pending_qty = row.pending_execution_qty or Decimal("0")
        projected_pending_qty = pending_qty - requested_qty
        options.append(
            PurchaseContractSelectOptionOut(
                purchase_contract_id=row.purchase_contract_id,
                contract_no=row.contract_no,
                supplier_company_id=row.supplier_company_id,
                supplier_company_name=row.supplier_company_name,
                product_id=row.product_id,
                product_name=row.product_name,
                unit_name=row.unit_name,
                pending_execution_qty_ton=float(pending_qty),
                projected_pending_execution_qty_ton=float(max(projected_pending_qty, Decimal("0"))),
                projected_over_execution_qty_ton=float(max(-projected_pending_qty, Decimal("0"))),
                default_sort_rank=index,
            )
        )
    return options


def build_sales_order_create_meta(db: Session, current_user: User) -> SalesOrderCreateMetaOut:
    contract_options = list_sales_contract_select_options(db=db, current_user=current_user)
    product_ids = {item.product_id for item in contract_options}
    warehouse_product_stock_pairs: list[SalesOrderCreateWarehouseProductStockOut] = []
    warehouse_ids: set[int] = set()
    if product_ids:
        inventory_rows = db.execute(
            select(InventoryBalance.warehouse_id, InventoryBalance.product_id)
            .join(Warehouse, Warehouse.id == InventoryBalance.warehouse_id)
            .where(
                InventoryBalance.product_id.in_(product_ids),
                InventoryBalance.on_hand_qty_ton > Decimal("0"),
                Warehouse.is_active.is_(True),
            )
            .order_by(InventoryBalance.warehouse_id.asc(), InventoryBalance.product_id.asc())
        ).all()
        warehouse_product_stock_pairs = [
            SalesOrderCreateWarehouseProductStockOut(
                warehouse_id=row.warehouse_id,
                product_id=row.product_id,
            )
            for row in inventory_rows
        ]
        warehouse_ids = {item.warehouse_id for item in warehouse_product_stock_pairs}

    warehouses: list[Warehouse] = []
    if warehouse_ids:
        warehouses = db.scalars(
            select(Warehouse)
            .where(
                Warehouse.id.in_(warehouse_ids),
                Warehouse.is_active.is_(True),
            )
            .order_by(Warehouse.name.asc(), Warehouse.id.asc())
        ).all()

    products: list[ProductSelectOptionOut] = []
    if product_ids:
        rows = db.scalars(
            select(OilProduct)
            .where(
                OilProduct.id.in_(product_ids),
                OilProduct.is_active.is_(True),
            )
            .order_by(OilProduct.name.asc(), OilProduct.id.asc())
        ).all()
        products = [ProductSelectOptionOut.model_validate(item) for item in rows]

    return SalesOrderCreateMetaOut(
        order_creation_enabled=bool(warehouses and contract_options and warehouse_product_stock_pairs),
        warehouses=[WarehouseSelectOptionOut.model_validate(item) for item in warehouses],
        products=products,
        sales_contracts=contract_options,
        warehouse_product_stock_pairs=warehouse_product_stock_pairs,
    )
