from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.master_data import OilProduct, Warehouse
from app.models.user import User, UserRole
from app.models.v5_domain import (
    Company,
    ContractStatus,
    CustomerTransportProfile,
    FileAsset,
    FileAssetLink,
    InventoryBalance,
    InventoryMovement,
    InventoryMovementType,
    PurchaseOrderV5,
    PurchaseOrderV5Status,
    SalesContract,
    SalesContractItem,
    SalesInventoryReservation,
    SalesInventoryReservationStatus,
    SalesOrderV5,
    SalesOrderV5Status,
)
from app.schemas.v5_sales_order import SalesOrderCreateRequest
from app.services.v5_file_asset_service import (
    build_protected_file_urls,
    ensure_file_asset,
    replace_file_asset_links,
)
from app.services.file_storage_service import build_protected_file_url_by_key


def build_sales_order_no(db: Session, order_date: date) -> str:
    count = db.scalar(
        select(func.count())
        .select_from(SalesOrderV5)
        .where(SalesOrderV5.order_date == order_date)
    )
    seq = int(count or 0) + 1
    return f"SO-{order_date.strftime('%Y%m%d')}-{seq:04d}"


def build_purchase_order_no(db: Session, order_date: date) -> str:
    count = db.scalar(select(func.count()).select_from(PurchaseOrderV5))
    seq = int(count or 0) + 1
    return f"PO-{order_date.strftime('%Y%m%d')}-{seq:04d}"


def _normalize_decimal(value: float, precision: str = "0.0000") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(precision))


def _build_tax_amounts(*, amount_tax_included: Decimal, tax_rate: Decimal | None) -> tuple[float | None, float | None]:
    if tax_rate is None:
        return None, None
    amount_tax_excluded = (amount_tax_included / (Decimal("1.0000") + tax_rate)).quantize(Decimal("0.01"))
    tax_amount = (amount_tax_included - amount_tax_excluded).quantize(Decimal("0.01"))
    return float(amount_tax_excluded), float(tax_amount)


def _require_customer_company(current_user: User) -> int:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer_company_not_bound")
    return current_user.company_id


def _list_pending_sales_order_statuses(current_user: User) -> tuple[SalesOrderV5Status, ...]:
    if current_user.role == UserRole.OPERATOR:
        return (SalesOrderV5Status.SUBMITTED,)
    if current_user.role == UserRole.FINANCE:
        return (SalesOrderV5Status.OPERATOR_APPROVED,)
    return (
        SalesOrderV5Status.SUBMITTED,
        SalesOrderV5Status.OPERATOR_APPROVED,
        SalesOrderV5Status.CUSTOMER_PAYMENT_CONFIRMED,
        SalesOrderV5Status.READY_FOR_OUTBOUND,
    )


def _require_sales_contract(
    db: Session,
    *,
    sales_contract_id: int,
    customer_company_id: int,
    product_id: int,
) -> tuple[SalesContract, SalesContractItem]:
    contract = db.scalar(
        select(SalesContract).where(
            SalesContract.id == sales_contract_id,
            SalesContract.customer_company_id == customer_company_id,
            SalesContract.status.in_((ContractStatus.EFFECTIVE, ContractStatus.PARTIALLY_EXECUTED)),
        )
    )
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sales_contract_not_found")

    item = db.scalar(
        select(SalesContractItem).where(
            SalesContractItem.sales_contract_id == contract.id,
            SalesContractItem.product_id == product_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_contract_product_not_match")
    if contract.pending_execution_qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_contract_pending_qty_empty")
    return contract, item


def _require_transport_profile(
    db: Session,
    *,
    transport_profile_id: int | None,
    customer_company_id: int,
) -> CustomerTransportProfile | None:
    if transport_profile_id is None:
        return None
    profile = db.scalar(
        select(CustomerTransportProfile).where(
            CustomerTransportProfile.id == transport_profile_id,
            CustomerTransportProfile.customer_company_id == customer_company_id,
        )
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="transport_profile_not_found")
    return profile


def _normalize_transport_text(value: object, *, optional: bool = False) -> str | None:
    text = str(value or "").strip()
    if optional and not text:
        return None
    return text


def _normalize_transport_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text:
        return None
    if text in {"1", "true", "yes", "y", "是", "带泵"}:
        return True
    if text in {"0", "false", "no", "n", "否", "不带泵"}:
        return False
    return bool(text)


def _normalize_transport_rated_load(value: object) -> int | None:
    if value in (None, ""):
        return None
    decimal_value = Decimal(str(value))
    return int(decimal_value)


def _normalize_transport_tank_type(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return {
        "单仓": "单枪",
        "双仓": "双枪",
        "单枪": "单枪",
        "双枪": "双枪",
    }.get(text, text)


def _normalize_transport_snapshot(snapshot: dict[str, object] | None) -> dict[str, object]:
    payload = snapshot or {}
    normalized_with_pump = _normalize_transport_bool(payload.get("with_pump"))
    return {
        "carrier_company": _normalize_transport_text(payload.get("carrier_company")) or "",
        "driver_name": _normalize_transport_text(payload.get("driver_name")) or "",
        "driver_phone": _normalize_transport_text(payload.get("driver_phone")) or "",
        "driver_id_no": _normalize_transport_text(payload.get("driver_id_no")) or "",
        "vehicle_no": _normalize_transport_text(payload.get("vehicle_no")) or "",
        "tank_type": _normalize_transport_tank_type(payload.get("tank_type")),
        "with_pump": normalized_with_pump if normalized_with_pump is not None else False,
        "rated_load_ton": _normalize_transport_rated_load(payload.get("rated_load_ton")),
        "remark": _normalize_transport_text(payload.get("remark"), optional=True),
    }


def _find_transport_profile_by_snapshot(
    db: Session,
    *,
    customer_company_id: int,
    normalized_snapshot: dict[str, object],
) -> CustomerTransportProfile | None:
    profiles = db.scalars(
        select(CustomerTransportProfile)
        .where(CustomerTransportProfile.customer_company_id == customer_company_id)
        .order_by(CustomerTransportProfile.id.asc())
    ).all()
    for profile in profiles:
        if _normalize_transport_snapshot(profile.transport_snapshot_json) == normalized_snapshot:
            return profile
    return None


def _resolve_transport_profile_for_order(
    db: Session,
    *,
    customer_company_id: int,
    transport_profile_id: int | None,
    transport_snapshot: dict[str, object],
    current_user: User,
) -> tuple[CustomerTransportProfile, dict[str, object]]:
    _require_transport_profile(
        db,
        transport_profile_id=transport_profile_id,
        customer_company_id=customer_company_id,
    )
    normalized_snapshot = _normalize_transport_snapshot(transport_snapshot)
    profile = _find_transport_profile_by_snapshot(
        db,
        customer_company_id=customer_company_id,
        normalized_snapshot=normalized_snapshot,
    )
    if profile is None:
        has_existing_profile = db.scalar(
            select(CustomerTransportProfile.id)
            .where(CustomerTransportProfile.customer_company_id == customer_company_id)
            .limit(1)
        )
        profile = CustomerTransportProfile(
            customer_company_id=customer_company_id,
            transport_snapshot_json=normalized_snapshot,
            is_default=has_existing_profile is None,
            created_by=current_user.id,
        )
        db.add(profile)
        db.flush()
    profile.last_used_at = datetime.now(UTC)
    return profile, normalized_snapshot


def _require_inventory_balance(db: Session, *, warehouse_id: int, product_id: int) -> InventoryBalance:
    row = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.warehouse_id == warehouse_id,
            InventoryBalance.product_id == product_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="inventory_balance_not_found")
    return row


def _require_warehouse_product_stock_for_create(
    db: Session,
    *,
    warehouse_id: int,
    product_id: int,
) -> InventoryBalance:
    inventory_balance = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.warehouse_id == warehouse_id,
            InventoryBalance.product_id == product_id,
        )
    )
    if inventory_balance is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="warehouse_product_inventory_not_found")
    if inventory_balance.on_hand_qty_ton <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="warehouse_product_inventory_empty")
    return inventory_balance


def _build_contract_snapshot(
    contract: SalesContract,
    item: SalesContractItem,
    *,
    customer_company_name: str | None,
    seller_company_name: str | None,
) -> dict[str, object]:
    return {
        "sales_contract_id": contract.id,
        "contract_no": contract.contract_no,
        "status": contract.status.value,
        "contract_business_direction": "销售",
        "counterparty_role_text": "买方",
        "customer_company_name": str(customer_company_name or "").strip(),
        "counterparty_company_name": str(customer_company_name or "").strip(),
        "buyer_company_name": str(customer_company_name or "").strip(),
        "seller_company_name": str(seller_company_name or "").strip(),
        "product_id": item.product_id,
        "unit_name": item.unit_name,
        "unit_price_tax_included": str(item.unit_price_tax_included),
        "pending_execution_qty": str(contract.pending_execution_qty),
    }


def _create_inventory_reservation(
    db: Session,
    *,
    sales_order: SalesOrderV5,
    inventory_balance: InventoryBalance,
    current_user: User,
) -> SalesInventoryReservation:
    if inventory_balance.available_qty_ton < sales_order.qty_ton:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="inventory_not_enough")

    reservation = db.scalar(
        select(SalesInventoryReservation).where(
            SalesInventoryReservation.sales_order_id == sales_order.id,
            SalesInventoryReservation.status == SalesInventoryReservationStatus.ACTIVE,
        )
    )
    if reservation is None:
        reservation = SalesInventoryReservation(
            sales_order_id=sales_order.id,
            inventory_balance_id=inventory_balance.id,
            reserved_qty_ton=sales_order.qty_ton,
            status=SalesInventoryReservationStatus.ACTIVE,
            created_by=current_user.id,
        )
        db.add(reservation)
    inventory_balance.reserved_qty_ton += sales_order.qty_ton
    inventory_balance.available_qty_ton -= sales_order.qty_ton
    sales_order.reserved_qty_ton = sales_order.qty_ton
    db.add(
        InventoryMovement(
            movement_no=f"MV-RES-{sales_order.sales_order_no}",
            warehouse_id=sales_order.warehouse_id,
            product_id=sales_order.product_id,
            movement_type=InventoryMovementType.SALES_RESERVE,
            business_type="SALES_ORDER",
            business_id=sales_order.id,
            before_on_hand_qty_ton=inventory_balance.on_hand_qty_ton,
            change_qty_ton=sales_order.qty_ton,
            after_on_hand_qty_ton=inventory_balance.on_hand_qty_ton,
            before_reserved_qty_ton=inventory_balance.reserved_qty_ton - sales_order.qty_ton,
            after_reserved_qty_ton=inventory_balance.reserved_qty_ton,
            operator_user_id=current_user.id,
            remark="销售订单运营审核冻结库存",
        )
    )
    return reservation


def _get_active_sales_reservation(db: Session, *, sales_order_id: int) -> SalesInventoryReservation | None:
    return db.scalar(
        select(SalesInventoryReservation).where(
            SalesInventoryReservation.sales_order_id == sales_order_id,
            SalesInventoryReservation.status == SalesInventoryReservationStatus.ACTIVE,
        )
    )


def release_sales_inventory_reservation(
    db: Session,
    *,
    sales_order: SalesOrderV5,
    current_user: User,
    reason: str,
) -> bool:
    reservation = _get_active_sales_reservation(db, sales_order_id=sales_order.id)
    if reservation is None:
        sales_order.reserved_qty_ton = Decimal("0.0000")
        return False

    inventory_balance = db.scalar(select(InventoryBalance).where(InventoryBalance.id == reservation.inventory_balance_id))
    if inventory_balance is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="inventory_balance_not_found")

    now = datetime.now(UTC)
    reserved_qty = reservation.reserved_qty_ton
    before_reserved = inventory_balance.reserved_qty_ton
    inventory_balance.reserved_qty_ton = (inventory_balance.reserved_qty_ton - reserved_qty).quantize(Decimal("0.0000"))
    inventory_balance.available_qty_ton = (inventory_balance.available_qty_ton + reserved_qty).quantize(Decimal("0.0000"))
    inventory_balance.last_movement_at = now
    reservation.status = SalesInventoryReservationStatus.RELEASED
    reservation.released_reason = reason
    reservation.released_at = now
    sales_order.reserved_qty_ton = Decimal("0.0000")
    db.add(
        InventoryMovement(
            movement_no=f"MV-REL-{sales_order.sales_order_no}",
            warehouse_id=sales_order.warehouse_id,
            product_id=sales_order.product_id,
            movement_type=InventoryMovementType.SALES_RESERVE_RELEASE,
            business_type="SALES_ORDER",
            business_id=sales_order.id,
            before_on_hand_qty_ton=inventory_balance.on_hand_qty_ton,
            change_qty_ton=reserved_qty,
            after_on_hand_qty_ton=inventory_balance.on_hand_qty_ton,
            before_reserved_qty_ton=before_reserved,
            after_reserved_qty_ton=inventory_balance.reserved_qty_ton,
            operator_user_id=current_user.id,
            remark=reason,
        )
    )
    return True


def _mark_sales_order_closed(
    sales_order: SalesOrderV5,
    *,
    target_status: SalesOrderV5Status,
    reason: str,
    current_user: User,
) -> None:
    now = datetime.now(UTC)
    sales_order.status = target_status
    sales_order.closed_reason = reason
    sales_order.closed_by = current_user.id
    sales_order.closed_at = now


def _mark_purchase_order_abnormal_closed(
    purchase_order: PurchaseOrderV5,
    *,
    reason: str,
    current_user: User,
) -> None:
    now = datetime.now(UTC)
    purchase_order.status = PurchaseOrderV5Status.ABNORMAL_CLOSED
    purchase_order.closed_reason = reason
    purchase_order.closed_by = current_user.id
    purchase_order.closed_at = now


def _serialize_sales_order_row(
    *,
    db: Session,
    sales_order: SalesOrderV5,
    customer_company_name: str,
    warehouse_name: str,
    product_name: str,
    sales_contract_no: str,
    purchase_order_id: int | None,
    contract_item_tax_rate: Decimal | None,
):
    from app.schemas.v5_sales_order import SalesOrderDetailOut, SalesOrderListItemOut

    transport_file_rows = db.execute(
        select(FileAsset.file_key, FileAsset.file_name)
        .join(FileAssetLink, FileAssetLink.file_asset_id == FileAsset.id)
        .where(
            FileAssetLink.entity_type == "SALES_ORDER",
            FileAssetLink.entity_id == sales_order.id,
            FileAssetLink.field_name == "transport_files",
        )
        .order_by(FileAssetLink.sort_no.asc(), FileAssetLink.id.asc())
    ).all()
    transport_file_keys = [row.file_key for row in transport_file_rows]
    transport_file_names = [row.file_name for row in transport_file_rows]
    customer_payment_receipt_file_key = None
    customer_payment_receipt_file_url = None
    customer_payment_receipt_file_name = None
    if sales_order.customer_payment_receipt_file_id is not None:
        customer_payment_receipt_file_row = db.execute(
            select(FileAsset.file_key, FileAsset.file_name).where(FileAsset.id == sales_order.customer_payment_receipt_file_id)
        ).one_or_none()
        if customer_payment_receipt_file_row is not None:
            customer_payment_receipt_file_key = customer_payment_receipt_file_row.file_key
            customer_payment_receipt_file_name = customer_payment_receipt_file_row.file_name
        if customer_payment_receipt_file_key:
            customer_payment_receipt_file_url = build_protected_file_url_by_key(customer_payment_receipt_file_key)
    amount_tax_excluded, tax_amount = _build_tax_amounts(
        amount_tax_included=sales_order.amount_tax_included,
        tax_rate=contract_item_tax_rate,
    )

    payload = {
        "id": sales_order.id,
        "sales_order_no": sales_order.sales_order_no,
        "order_date": sales_order.order_date,
        "customer_company_id": sales_order.customer_company_id,
        "customer_company_name": customer_company_name,
        "warehouse_id": sales_order.warehouse_id,
        "warehouse_name": warehouse_name,
        "product_id": sales_order.product_id,
        "product_name": product_name,
        "sales_contract_id": sales_order.sales_contract_id,
        "sales_contract_no": sales_contract_no,
        "buyer_company_name": customer_company_name or None,
        "seller_company_name": _resolve_sales_contract_seller_name(
            contract_snapshot=sales_order.sales_contract_snapshot_json,
            operator_company_name=sales_order.operator_company_name_snapshot,
        ),
        "contract_signing_subject_name": _resolve_sales_contract_signing_subject_name(
            contract_snapshot=sales_order.sales_contract_snapshot_json,
            customer_company_name=customer_company_name,
        ),
        "qty_ton": float(sales_order.qty_ton),
        "unit_price_tax_included": float(sales_order.unit_price_tax_included),
        "amount_tax_included": float(sales_order.amount_tax_included),
        "amount_tax_excluded": amount_tax_excluded,
        "tax_amount": tax_amount,
        "status": sales_order.status,
        "reserved_qty_ton": float(sales_order.reserved_qty_ton),
        "actual_outbound_qty_ton": float(sales_order.actual_outbound_qty_ton),
        "received_amount": float(sales_order.received_amount) if sales_order.received_amount is not None else None,
        "closed_reason": sales_order.closed_reason,
        "closed_by": sales_order.closed_by,
        "closed_at": sales_order.closed_at,
        "created_at": sales_order.created_at,
        "updated_at": sales_order.updated_at,
        "transport_profile_id": sales_order.transport_profile_id,
        "transport_snapshot": sales_order.transport_snapshot_json,
        "transport_file_keys": transport_file_keys,
        "transport_file_names": transport_file_names,
        "transport_file_urls": build_protected_file_urls(transport_file_keys),
        "customer_payment_receipt_file_key": customer_payment_receipt_file_key,
        "customer_payment_receipt_file_url": customer_payment_receipt_file_url,
        "customer_payment_receipt_file_name": customer_payment_receipt_file_name,
        "operator_company_id": sales_order.operator_company_id,
        "operator_company_name_snapshot": sales_order.operator_company_name_snapshot,
        "operator_reviewed_by": sales_order.operator_reviewed_by,
        "operator_reviewed_at": sales_order.operator_reviewed_at,
        "finance_reviewed_by": sales_order.finance_reviewed_by,
        "finance_reviewed_at": sales_order.finance_reviewed_at,
        "purchase_order_id": purchase_order_id,
    }
    return SalesOrderListItemOut(**payload), SalesOrderDetailOut(**payload)


def create_sales_order(db: Session, *, payload: SalesOrderCreateRequest, current_user: User) -> SalesOrderV5:
    customer_company_id = _require_customer_company(current_user)
    warehouse = db.scalar(select(Warehouse).where(Warehouse.id == payload.warehouse_id, Warehouse.is_active.is_(True)))
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="warehouse_not_found")
    product = db.scalar(select(OilProduct).where(OilProduct.id == payload.product_id, OilProduct.is_active.is_(True)))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product_not_found")

    contract, contract_item = _require_sales_contract(
        db,
        sales_contract_id=payload.sales_contract_id,
        customer_company_id=customer_company_id,
        product_id=payload.product_id,
    )
    _require_warehouse_product_stock_for_create(
        db,
        warehouse_id=payload.warehouse_id,
        product_id=payload.product_id,
    )
    transport_profile, normalized_transport_snapshot = _resolve_transport_profile_for_order(
        db,
        customer_company_id=customer_company_id,
        transport_profile_id=payload.transport_profile_id,
        transport_snapshot=payload.transport_snapshot.model_dump(),
        current_user=current_user,
    )
    qty_ton = _normalize_decimal(payload.qty_ton)
    amount_tax_included = (contract_item.unit_price_tax_included * qty_ton).quantize(Decimal("0.01"))
    sales_order = SalesOrderV5(
        sales_order_no=build_sales_order_no(db, payload.order_date),
        order_date=payload.order_date,
        customer_company_id=customer_company_id,
        warehouse_id=payload.warehouse_id,
        product_id=payload.product_id,
        sales_contract_id=contract.id,
        sales_contract_snapshot_json=_build_contract_snapshot(
            contract,
            contract_item,
            customer_company_name=current_user.company_name_snapshot,
            seller_company_name=(contract.variable_snapshot_json or {}).get("seller_company_name"),
        ),
        qty_ton=qty_ton,
        unit_price_tax_included=contract_item.unit_price_tax_included,
        amount_tax_included=amount_tax_included,
        transport_profile_id=transport_profile.id,
        transport_snapshot_json=normalized_transport_snapshot,
        created_by=current_user.id,
    )
    db.add(sales_order)
    db.flush()

    transport_file_asset_ids: list[int] = []
    for file_key in payload.transport_file_keys:
        asset = ensure_file_asset(
            db,
            file_key=file_key,
            business_type="sales_order_transport",
            current_user=current_user,
        )
        transport_file_asset_ids.append(asset.id)
    replace_file_asset_links(
        db,
        entity_type="SALES_ORDER",
        entity_id=sales_order.id,
        field_name="transport_files",
        file_asset_ids=transport_file_asset_ids,
    )
    return sales_order


def _resolve_sales_contract_seller_name(
    *,
    contract_snapshot: dict[str, object] | None,
    operator_company_name: str | None,
) -> str | None:
    snapshot_name = str((contract_snapshot or {}).get("seller_company_name") or "").strip()
    if snapshot_name:
        return snapshot_name
    current_name = str(operator_company_name or "").strip()
    return current_name or None


def _resolve_sales_contract_signing_subject_name(
    *,
    contract_snapshot: dict[str, object] | None,
    customer_company_name: str | None,
) -> str | None:
    buyer_name = str((contract_snapshot or {}).get("buyer_company_name") or "").strip()
    if buyer_name:
        return buyer_name
    snapshot_name = str((contract_snapshot or {}).get("customer_company_name") or "").strip()
    if snapshot_name:
        return snapshot_name
    current_name = str(customer_company_name or "").strip()
    return current_name or None


def apply_operator_review(db: Session, *, sales_order: SalesOrderV5, current_user: User) -> SalesOrderV5:
    if sales_order.status != SalesOrderV5Status.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_order_status_invalid")
    inventory_balance = _require_inventory_balance(
        db,
        warehouse_id=sales_order.warehouse_id,
        product_id=sales_order.product_id,
    )
    _create_inventory_reservation(
        db,
        sales_order=sales_order,
        inventory_balance=inventory_balance,
        current_user=current_user,
    )
    sales_order.status = SalesOrderV5Status.OPERATOR_APPROVED
    sales_order.operator_reviewed_by = current_user.id
    sales_order.operator_reviewed_at = datetime.now(UTC)
    sales_order.operator_company_id = current_user.company_id
    sales_order.operator_company_name_snapshot = current_user.company_name_snapshot
    return sales_order


def apply_finance_review(
    db: Session,
    *,
    sales_order: SalesOrderV5,
    received_amount: float,
    customer_payment_receipt_file_key: str,
    current_user: User,
) -> tuple[SalesOrderV5, PurchaseOrderV5, bool]:
    if sales_order.status != SalesOrderV5Status.OPERATOR_APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_order_status_invalid")

    receipt_asset = ensure_file_asset(
        db,
        file_key=customer_payment_receipt_file_key,
        business_type="customer_payment_receipt",
        current_user=current_user,
    )
    purchase_order = db.scalar(select(PurchaseOrderV5).where(PurchaseOrderV5.sales_order_id == sales_order.id))
    purchase_order_created = False
    if purchase_order is None:
        purchase_order = PurchaseOrderV5(
            purchase_order_no=build_purchase_order_no(db, sales_order.order_date),
            sales_order_id=sales_order.id,
            warehouse_id=sales_order.warehouse_id,
            product_id=sales_order.product_id,
            qty_ton=sales_order.qty_ton,
            status=PurchaseOrderV5Status.PENDING_SUBMIT,
        )
        db.add(purchase_order)
        purchase_order_created = True

    sales_order.received_amount = Decimal(str(received_amount)).quantize(Decimal("0.01"))
    sales_order.customer_payment_receipt_file_id = receipt_asset.id
    sales_order.status = SalesOrderV5Status.CUSTOMER_PAYMENT_CONFIRMED
    sales_order.finance_reviewed_by = current_user.id
    sales_order.finance_reviewed_at = datetime.now(UTC)
    db.flush()
    return sales_order, purchase_order, purchase_order_created


def reject_sales_order(
    db: Session,
    *,
    sales_order: SalesOrderV5,
    reason: str,
    current_user: User,
) -> SalesOrderV5:
    if sales_order.status not in (SalesOrderV5Status.SUBMITTED, SalesOrderV5Status.OPERATOR_APPROVED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_order_status_invalid")
    release_sales_inventory_reservation(
        db,
        sales_order=sales_order,
        current_user=current_user,
        reason=f"销售订单驳回释放库存：{reason}",
    )
    _mark_sales_order_closed(
        sales_order,
        target_status=SalesOrderV5Status.REJECTED,
        reason=reason,
        current_user=current_user,
    )
    return sales_order


def abnormal_close_sales_order(
    db: Session,
    *,
    sales_order: SalesOrderV5,
    reason: str,
    current_user: User,
) -> tuple[SalesOrderV5, PurchaseOrderV5 | None]:
    if sales_order.status not in (SalesOrderV5Status.CUSTOMER_PAYMENT_CONFIRMED, SalesOrderV5Status.READY_FOR_OUTBOUND):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_order_status_invalid")

    purchase_order = db.scalar(select(PurchaseOrderV5).where(PurchaseOrderV5.sales_order_id == sales_order.id))
    if purchase_order is not None and purchase_order.status not in (
        PurchaseOrderV5Status.COMPLETED,
        PurchaseOrderV5Status.ABNORMAL_CLOSED,
    ):
        _mark_purchase_order_abnormal_closed(
            purchase_order,
            reason=reason,
            current_user=current_user,
        )
    release_sales_inventory_reservation(
        db,
        sales_order=sales_order,
        current_user=current_user,
        reason=f"销售订单异常关闭释放库存：{reason}",
    )
    _mark_sales_order_closed(
        sales_order,
        target_status=SalesOrderV5Status.ABNORMAL_CLOSED,
        reason=reason,
        current_user=current_user,
    )
    return sales_order, purchase_order


def get_sales_order_with_scope(
    db: Session,
    *,
    sales_order_id: int,
    current_user: User,
) -> SalesOrderV5:
    query = select(SalesOrderV5).where(SalesOrderV5.id == sales_order_id)
    if current_user.role == UserRole.CUSTOMER:
        query = query.where(SalesOrderV5.customer_company_id == _require_customer_company(current_user))
    row = db.scalar(query)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sales_order_not_found")
    return row


def list_sales_orders(
    db: Session,
    *,
    current_user: User,
    status_value: SalesOrderV5Status | None,
    pending_only: bool,
    from_date: date | None,
    to_date: date | None,
    page: int,
    page_size: int,
) -> list[SalesOrderV5]:
    query = select(SalesOrderV5)
    if current_user.role == UserRole.CUSTOMER:
        query = query.where(SalesOrderV5.customer_company_id == _require_customer_company(current_user))
    if status_value is not None:
        query = query.where(SalesOrderV5.status == status_value)
    if pending_only:
        query = query.where(SalesOrderV5.status.in_(_list_pending_sales_order_statuses(current_user)))
    if from_date is not None:
        query = query.where(SalesOrderV5.order_date >= from_date)
    if to_date is not None:
        query = query.where(SalesOrderV5.order_date <= to_date)
    query = query.order_by(SalesOrderV5.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(query).all()


def serialize_sales_order_list(db: Session, sales_orders: list[SalesOrderV5]):
    from app.schemas.v5_sales_order import SalesOrderListItemOut

    if not sales_orders:
        return []
    customer_company_ids = {item.customer_company_id for item in sales_orders}
    warehouse_ids = {item.warehouse_id for item in sales_orders}
    product_ids = {item.product_id for item in sales_orders}
    contract_ids = {item.sales_contract_id for item in sales_orders}
    order_ids = {item.id for item in sales_orders}
    sales_contract_item_tax_rate_map = {
        (row.sales_contract_id, row.product_id): row.tax_rate
        for row in db.scalars(
            select(SalesContractItem).where(
                SalesContractItem.sales_contract_id.in_(contract_ids),
                SalesContractItem.product_id.in_(product_ids),
            )
        ).all()
    }

    customer_name_map = dict(
        db.execute(select(Company.id, Company.company_name).where(Company.id.in_(customer_company_ids))).all()
    )
    warehouse_name_map = dict(db.execute(select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(warehouse_ids))).all())
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(product_ids))).all())
    contract_no_map = dict(db.execute(select(SalesContract.id, SalesContract.contract_no).where(SalesContract.id.in_(contract_ids))).all())
    purchase_order_map = dict(
        db.execute(select(PurchaseOrderV5.sales_order_id, PurchaseOrderV5.id).where(PurchaseOrderV5.sales_order_id.in_(order_ids))).all()
    )

    result: list[SalesOrderListItemOut] = []
    for item in sales_orders:
        list_item, _ = _serialize_sales_order_row(
            db=db,
            sales_order=item,
            customer_company_name=customer_name_map.get(item.customer_company_id, ""),
            warehouse_name=warehouse_name_map.get(item.warehouse_id, ""),
            product_name=product_name_map.get(item.product_id, ""),
            sales_contract_no=contract_no_map.get(item.sales_contract_id, ""),
            purchase_order_id=purchase_order_map.get(item.id),
            contract_item_tax_rate=sales_contract_item_tax_rate_map.get((item.sales_contract_id, item.product_id)),
        )
        result.append(list_item)
    return result


def serialize_sales_order_detail(db: Session, sales_order: SalesOrderV5):
    customer_company_name = db.scalar(select(Company.company_name).where(Company.id == sales_order.customer_company_id)) or ""
    warehouse_name = db.scalar(select(Warehouse.name).where(Warehouse.id == sales_order.warehouse_id)) or ""
    product_name = db.scalar(select(OilProduct.name).where(OilProduct.id == sales_order.product_id)) or ""
    sales_contract_no = db.scalar(select(SalesContract.contract_no).where(SalesContract.id == sales_order.sales_contract_id)) or ""
    purchase_order_id = db.scalar(select(PurchaseOrderV5.id).where(PurchaseOrderV5.sales_order_id == sales_order.id))
    contract_item_tax_rate = db.scalar(
        select(SalesContractItem.tax_rate).where(
            SalesContractItem.sales_contract_id == sales_order.sales_contract_id,
            SalesContractItem.product_id == sales_order.product_id,
        )
    )
    _, detail = _serialize_sales_order_row(
        db=db,
        sales_order=sales_order,
        customer_company_name=customer_company_name,
        warehouse_name=warehouse_name,
        product_name=product_name,
        sales_contract_no=sales_contract_no,
        purchase_order_id=purchase_order_id,
        contract_item_tax_rate=contract_item_tax_rate,
    )
    return detail
