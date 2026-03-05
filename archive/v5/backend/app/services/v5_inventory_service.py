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
    InventoryAdjustment,
    InventoryAdjustmentType,
    InventoryBalance,
    InventoryMovement,
    InventoryMovementType,
    PurchaseContract,
    PurchaseContractItem,
    PurchaseStockIn,
    PurchaseStockInSourceKind,
    PurchaseStockInStatus,
)
from app.schemas.v5_inventory import (
    InventoryAdjustmentCreateRequest,
    InventoryAdjustmentOut,
    InventoryMovementOut,
    InventorySummaryProductItemOut,
    InventorySummaryProductWarehouseItemOut,
    InventorySummaryOut,
    InventorySummaryWarehouseItemOut,
    InventorySummaryWarehouseProductItemOut,
    PurchaseStockInDetailOut,
    PurchaseStockInListItemOut,
)


def _normalize_decimal(value: float, precision: str = "0.0000") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(precision))


def _extract_sequence_from_document_no(document_no: str, prefix: str) -> int:
    text = str(document_no or "").strip()
    if not text.startswith(prefix):
        return 0
    suffix = text[len(prefix):]
    if not suffix.isdigit():
        return 0
    return int(suffix)


def build_purchase_stock_in_no(db: Session, *, stock_in_date: date) -> str:
    prefix = f"PSI-{stock_in_date.strftime('%Y%m%d')}-"
    existing_numbers = db.scalars(
        select(PurchaseStockIn.stock_in_no).where(PurchaseStockIn.stock_in_no.like(f"{prefix}%"))
    ).all()
    max_seq = max((_extract_sequence_from_document_no(item, prefix) for item in existing_numbers), default=0)
    return f"{prefix}{max_seq + 1:04d}"


def build_inventory_adjustment_no(db: Session, *, adjust_date: date) -> str:
    count = db.scalar(select(func.count()).select_from(InventoryAdjustment))
    seq = int(count or 0) + 1
    return f"IAD-{adjust_date.strftime('%Y%m%d')}-{seq:04d}"


def _resolve_inventory_scope_filter(db: Session, current_user: User):
    if current_user.role != UserRole.WAREHOUSE:
        return None
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_not_bound")
    warehouse_ids = db.scalars(select(Warehouse.id).where(Warehouse.company_id == current_user.company_id)).all()
    if not warehouse_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="warehouse_company_not_bound")
    return warehouse_ids


def _get_or_create_inventory_balance(db: Session, *, warehouse_id: int, product_id: int) -> InventoryBalance:
    row = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.warehouse_id == warehouse_id,
            InventoryBalance.product_id == product_id,
        )
    )
    if row is not None:
        return row
    row = InventoryBalance(
        warehouse_id=warehouse_id,
        product_id=product_id,
        on_hand_qty_ton=Decimal("0.0000"),
        reserved_qty_ton=Decimal("0.0000"),
        available_qty_ton=Decimal("0.0000"),
    )
    db.add(row)
    db.flush()
    return row


def get_purchase_stock_in_with_scope(db: Session, *, stock_in_id: int, current_user: User) -> PurchaseStockIn:
    del current_user
    row = db.scalar(select(PurchaseStockIn).where(PurchaseStockIn.id == stock_in_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="purchase_stock_in_not_found")
    return row


def list_purchase_stock_ins(
    db: Session,
    *,
    status_value: PurchaseStockInStatus | None,
    page: int,
    page_size: int,
) -> list[PurchaseStockIn]:
    query = select(PurchaseStockIn)
    if status_value is not None:
        query = query.where(PurchaseStockIn.status == status_value)
    query = query.order_by(PurchaseStockIn.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(query).all()


def confirm_purchase_stock_in(
    db: Session,
    *,
    purchase_stock_in: PurchaseStockIn,
    payload,
    current_user: User,
) -> PurchaseStockIn:
    if purchase_stock_in.status != PurchaseStockInStatus.PENDING_CONFIRM:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_stock_in_status_invalid")

    purchase_contract = db.scalar(select(PurchaseContract).where(PurchaseContract.id == purchase_stock_in.purchase_contract_id))
    if purchase_contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="purchase_contract_not_found")
    if purchase_contract.status not in (ContractStatus.EFFECTIVE, ContractStatus.PARTIALLY_EXECUTED, ContractStatus.COMPLETED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_status_invalid")

    warehouse = db.scalar(select(Warehouse).where(Warehouse.id == payload.warehouse_id, Warehouse.is_active.is_(True)))
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="warehouse_not_found")
    product = db.scalar(select(OilProduct).where(OilProduct.id == payload.product_id, OilProduct.is_active.is_(True)))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product_not_found")
    contract_item = db.scalar(
        select(PurchaseContractItem).where(
            PurchaseContractItem.purchase_contract_id == purchase_contract.id,
            PurchaseContractItem.product_id == payload.product_id,
        )
    )
    if contract_item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_product_not_match")

    stock_in_qty = _normalize_decimal(payload.stock_in_qty)
    if stock_in_qty > purchase_contract.pending_stock_in_qty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_pending_stock_in_not_enough")

    purchase_stock_in.warehouse_id = payload.warehouse_id
    purchase_stock_in.product_id = payload.product_id
    purchase_stock_in.stock_in_qty_ton = stock_in_qty
    purchase_stock_in.stock_in_date = payload.stock_in_date
    purchase_stock_in.remark = payload.remark

    inventory_balance = _get_or_create_inventory_balance(
        db,
        warehouse_id=payload.warehouse_id,
        product_id=payload.product_id,
    )
    before_on_hand = inventory_balance.on_hand_qty_ton
    before_reserved = inventory_balance.reserved_qty_ton
    inventory_balance.on_hand_qty_ton = (inventory_balance.on_hand_qty_ton + stock_in_qty).quantize(Decimal("0.0000"))
    inventory_balance.available_qty_ton = (inventory_balance.available_qty_ton + stock_in_qty).quantize(Decimal("0.0000"))
    inventory_balance.last_movement_at = datetime.now(UTC)

    purchase_contract.stocked_in_qty = (purchase_contract.stocked_in_qty + stock_in_qty).quantize(Decimal("0.0000"))
    purchase_contract.pending_stock_in_qty = (purchase_contract.pending_stock_in_qty - stock_in_qty).quantize(Decimal("0.0000"))

    purchase_stock_in.status = PurchaseStockInStatus.CONFIRMED
    purchase_stock_in.confirmed_by = current_user.id
    purchase_stock_in.confirmed_at = datetime.now(UTC)

    movement_type = (
        InventoryMovementType.PURCHASE_SUPPLEMENT_STOCK_IN
        if purchase_stock_in.source_kind == PurchaseStockInSourceKind.SUPPLEMENT_AUTO
        else InventoryMovementType.PURCHASE_STOCK_IN
    )
    db.add(
        InventoryMovement(
            movement_no=f"MV-IN-{purchase_stock_in.stock_in_no}",
            warehouse_id=payload.warehouse_id,
            product_id=payload.product_id,
            movement_type=movement_type,
            business_type="PURCHASE_STOCK_IN",
            business_id=purchase_stock_in.id,
            before_on_hand_qty_ton=before_on_hand,
            change_qty_ton=stock_in_qty,
            after_on_hand_qty_ton=inventory_balance.on_hand_qty_ton,
            before_reserved_qty_ton=before_reserved,
            after_reserved_qty_ton=inventory_balance.reserved_qty_ton,
            operator_user_id=current_user.id,
            remark=payload.remark or "采购入库确认",
        )
    )
    return purchase_stock_in


def list_inventory_adjustments(
    db: Session,
    *,
    page: int,
    page_size: int,
) -> list[InventoryAdjustment]:
    return db.scalars(
        select(InventoryAdjustment).order_by(InventoryAdjustment.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()


def create_inventory_adjustment(
    db: Session,
    *,
    payload: InventoryAdjustmentCreateRequest,
    current_user: User,
) -> InventoryAdjustment:
    warehouse = db.scalar(select(Warehouse).where(Warehouse.id == payload.warehouse_id, Warehouse.is_active.is_(True)))
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="warehouse_not_found")
    product = db.scalar(select(OilProduct).where(OilProduct.id == payload.product_id, OilProduct.is_active.is_(True)))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product_not_found")

    inventory_balance = _get_or_create_inventory_balance(db, warehouse_id=payload.warehouse_id, product_id=payload.product_id)
    before_qty = _normalize_decimal(payload.before_qty)
    adjust_qty = _normalize_decimal(payload.adjust_qty)
    after_qty = _normalize_decimal(payload.after_qty)

    if inventory_balance.on_hand_qty_ton != before_qty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="inventory_before_qty_not_match")
    if after_qty < inventory_balance.reserved_qty_ton:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="inventory_after_qty_less_than_reserved")

    adjustment_no = build_inventory_adjustment_no(db, adjust_date=date.today())
    adjustment = InventoryAdjustment(
        adjustment_no=adjustment_no,
        warehouse_id=payload.warehouse_id,
        product_id=payload.product_id,
        adjust_type=payload.adjust_type,
        before_qty_ton=before_qty,
        adjust_qty_ton=adjust_qty,
        after_qty_ton=after_qty,
        reason=payload.reason,
        created_by=current_user.id,
    )
    db.add(adjustment)
    db.flush()

    before_reserved = inventory_balance.reserved_qty_ton
    inventory_balance.on_hand_qty_ton = after_qty
    inventory_balance.available_qty_ton = (after_qty - inventory_balance.reserved_qty_ton).quantize(Decimal("0.0000"))
    inventory_balance.last_movement_at = datetime.now(UTC)
    db.add(
        InventoryMovement(
            movement_no=f"MV-ADJ-{adjustment.adjustment_no}",
            warehouse_id=payload.warehouse_id,
            product_id=payload.product_id,
            movement_type=InventoryMovementType.INVENTORY_ADJUSTMENT,
            business_type="INVENTORY_ADJUSTMENT",
            business_id=adjustment.id,
            before_on_hand_qty_ton=before_qty,
            change_qty_ton=adjust_qty,
            after_on_hand_qty_ton=after_qty,
            before_reserved_qty_ton=before_reserved,
            after_reserved_qty_ton=inventory_balance.reserved_qty_ton,
            operator_user_id=current_user.id,
            remark=payload.reason,
        )
    )
    return adjustment


def summarize_inventory(
    db: Session,
    *,
    current_user: User,
    low_stock_threshold: float,
) -> InventorySummaryOut:
    scope_warehouse_ids = _resolve_inventory_scope_filter(db, current_user)
    query = select(InventoryBalance)
    if scope_warehouse_ids is not None:
        query = query.where(InventoryBalance.warehouse_id.in_(scope_warehouse_ids))
    rows = db.scalars(query).all()
    warehouse_ids = {row.warehouse_id for row in rows}
    product_ids = {row.product_id for row in rows}
    warehouse_name_map = dict(db.execute(select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(warehouse_ids))).all()) if warehouse_ids else {}
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(product_ids))).all()) if product_ids else {}

    low_threshold = _normalize_decimal(low_stock_threshold)
    summary_items: list[InventorySummaryWarehouseItemOut] = []
    for warehouse_id in sorted(warehouse_ids):
        warehouse_rows = [item for item in rows if item.warehouse_id == warehouse_id]
        summary_items.append(
            InventorySummaryWarehouseItemOut(
                warehouse_id=warehouse_id,
                warehouse_name=warehouse_name_map.get(warehouse_id, ""),
                total_on_hand_qty_ton=float(sum(item.on_hand_qty_ton for item in warehouse_rows)),
                total_reserved_qty_ton=float(sum(item.reserved_qty_ton for item in warehouse_rows)),
                total_available_qty_ton=float(sum(item.available_qty_ton for item in warehouse_rows)),
                low_stock_item_count=sum(1 for item in warehouse_rows if item.available_qty_ton <= low_threshold),
                product_items=[
                    InventorySummaryWarehouseProductItemOut(
                        product_id=item.product_id,
                        product_name=product_name_map.get(item.product_id, ""),
                        on_hand_qty_ton=float(item.on_hand_qty_ton),
                        reserved_qty_ton=float(item.reserved_qty_ton),
                        available_qty_ton=float(item.available_qty_ton),
                    )
                    for item in sorted(warehouse_rows, key=lambda row: (product_name_map.get(row.product_id, ""), row.product_id))
                ],
            )
        )

    product_items: list[InventorySummaryProductItemOut] = []
    for product_id in sorted(product_ids):
        product_rows = [item for item in rows if item.product_id == product_id]
        product_items.append(
            InventorySummaryProductItemOut(
                product_id=product_id,
                product_name=product_name_map.get(product_id, ""),
                total_on_hand_qty_ton=float(sum(item.on_hand_qty_ton for item in product_rows)),
                total_reserved_qty_ton=float(sum(item.reserved_qty_ton for item in product_rows)),
                total_available_qty_ton=float(sum(item.available_qty_ton for item in product_rows)),
                warehouse_items=[
                    InventorySummaryProductWarehouseItemOut(
                        warehouse_id=item.warehouse_id,
                        warehouse_name=warehouse_name_map.get(item.warehouse_id, ""),
                        on_hand_qty_ton=float(item.on_hand_qty_ton),
                        reserved_qty_ton=float(item.reserved_qty_ton),
                        available_qty_ton=float(item.available_qty_ton),
                    )
                    for item in sorted(product_rows, key=lambda row: (warehouse_name_map.get(row.warehouse_id, ""), row.warehouse_id))
                ],
            )
        )

    return InventorySummaryOut(
        total_on_hand_qty_ton=float(sum(item.on_hand_qty_ton for item in rows)),
        total_reserved_qty_ton=float(sum(item.reserved_qty_ton for item in rows)),
        total_available_qty_ton=float(sum(item.available_qty_ton for item in rows)),
        low_stock_threshold=low_stock_threshold,
        warehouse_items=summary_items,
        product_items=product_items,
    )


def list_inventory_movements(
    db: Session,
    *,
    warehouse_id: int | None,
    product_id: int | None,
    from_date: date | None,
    to_date: date | None,
    page: int,
    page_size: int,
) -> list[InventoryMovement]:
    query = select(InventoryMovement)
    if warehouse_id is not None:
        query = query.where(InventoryMovement.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.where(InventoryMovement.product_id == product_id)
    if from_date is not None:
        query = query.where(InventoryMovement.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date is not None:
        query = query.where(InventoryMovement.created_at < datetime.combine(to_date, datetime.max.time()))
    query = query.order_by(InventoryMovement.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(query).all()


def serialize_purchase_stock_in_list(db: Session, *, rows: list[PurchaseStockIn]) -> list[PurchaseStockInListItemOut]:
    if not rows:
        return []
    contract_ids = {item.purchase_contract_id for item in rows}
    warehouse_ids = {item.warehouse_id for item in rows}
    product_ids = {item.product_id for item in rows}
    contracts = {item.id: item for item in db.scalars(select(PurchaseContract).where(PurchaseContract.id.in_(contract_ids))).all()}
    supplier_company_ids = {item.supplier_company_id for item in contracts.values()}
    supplier_name_map = dict(db.execute(select(Company.id, Company.company_name).where(Company.id.in_(supplier_company_ids))).all())
    warehouse_name_map = dict(db.execute(select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(warehouse_ids))).all()) if warehouse_ids else {}
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(product_ids))).all()) if product_ids else {}

    result: list[PurchaseStockInListItemOut] = []
    for item in rows:
        contract = contracts[item.purchase_contract_id]
        result.append(
            PurchaseStockInListItemOut(
                id=item.id,
                stock_in_no=item.stock_in_no,
                purchase_contract_id=contract.id,
                purchase_contract_no=contract.contract_no,
                supplier_company_id=contract.supplier_company_id,
                supplier_company_name=supplier_name_map.get(contract.supplier_company_id, ""),
                warehouse_id=item.warehouse_id,
                warehouse_name=warehouse_name_map.get(item.warehouse_id, ""),
                product_id=item.product_id,
                product_name=product_name_map.get(item.product_id, ""),
                stock_in_qty_ton=float(item.stock_in_qty_ton),
                stock_in_date=item.stock_in_date,
                status=item.status,
                source_kind=item.source_kind,
                remark=item.remark,
                confirmed_by=item.confirmed_by,
                confirmed_at=item.confirmed_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return result


def serialize_purchase_stock_in_detail(db: Session, *, row: PurchaseStockIn) -> PurchaseStockInDetailOut:
    contract = db.scalar(select(PurchaseContract).where(PurchaseContract.id == row.purchase_contract_id))
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="purchase_contract_not_found")
    supplier_company_name = db.scalar(select(Company.company_name).where(Company.id == contract.supplier_company_id)) or ""
    warehouse_name = db.scalar(select(Warehouse.name).where(Warehouse.id == row.warehouse_id)) or ""
    product_name = db.scalar(select(OilProduct.name).where(OilProduct.id == row.product_id)) or ""
    return PurchaseStockInDetailOut(
        id=row.id,
        stock_in_no=row.stock_in_no,
        purchase_contract_id=contract.id,
        purchase_contract_no=contract.contract_no,
        supplier_company_id=contract.supplier_company_id,
        supplier_company_name=supplier_company_name,
        warehouse_id=row.warehouse_id,
        warehouse_name=warehouse_name,
        product_id=row.product_id,
        product_name=product_name,
        stock_in_qty_ton=float(row.stock_in_qty_ton),
        stock_in_date=row.stock_in_date,
        status=row.status,
        source_kind=row.source_kind,
        remark=row.remark,
        confirmed_by=row.confirmed_by,
        confirmed_at=row.confirmed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        purchase_contract_status=contract.status.value,
        purchase_contract_stocked_in_qty=float(contract.stocked_in_qty),
        purchase_contract_pending_stock_in_qty=float(contract.pending_stock_in_qty),
    )


def serialize_inventory_adjustment_list(db: Session, *, rows: list[InventoryAdjustment]) -> list[InventoryAdjustmentOut]:
    if not rows:
        return []
    warehouse_ids = {item.warehouse_id for item in rows}
    product_ids = {item.product_id for item in rows}
    warehouse_name_map = dict(db.execute(select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(warehouse_ids))).all()) if warehouse_ids else {}
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(product_ids))).all()) if product_ids else {}
    return [
        InventoryAdjustmentOut(
            id=item.id,
            adjustment_no=item.adjustment_no,
            warehouse_id=item.warehouse_id,
            warehouse_name=warehouse_name_map.get(item.warehouse_id, ""),
            product_id=item.product_id,
            product_name=product_name_map.get(item.product_id, ""),
            adjust_type=item.adjust_type,
            before_qty_ton=float(item.before_qty_ton),
            adjust_qty_ton=float(item.adjust_qty_ton),
            after_qty_ton=float(item.after_qty_ton),
            reason=item.reason,
            created_by=item.created_by,
            created_at=item.created_at,
        )
        for item in rows
    ]


def serialize_inventory_movement_list(db: Session, *, rows: list[InventoryMovement]) -> list[InventoryMovementOut]:
    if not rows:
        return []
    warehouse_ids = {item.warehouse_id for item in rows}
    product_ids = {item.product_id for item in rows}
    user_ids = {item.operator_user_id for item in rows}
    warehouse_name_map = dict(db.execute(select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(warehouse_ids))).all()) if warehouse_ids else {}
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(product_ids))).all()) if product_ids else {}
    user_name_map = {
        item.id: (item.username or item.display_name or f"用户{item.id}")
        for item in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    } if user_ids else {}
    return [
        InventoryMovementOut(
            id=item.id,
            movement_no=item.movement_no,
            warehouse_id=item.warehouse_id,
            warehouse_name=warehouse_name_map.get(item.warehouse_id, ""),
            product_id=item.product_id,
            product_name=product_name_map.get(item.product_id, ""),
            movement_type=item.movement_type,
            business_type=item.business_type,
            business_id=item.business_id,
            before_on_hand_qty_ton=float(item.before_on_hand_qty_ton),
            change_qty_ton=float(item.change_qty_ton),
            after_on_hand_qty_ton=float(item.after_on_hand_qty_ton),
            before_reserved_qty_ton=float(item.before_reserved_qty_ton),
            after_reserved_qty_ton=float(item.after_reserved_qty_ton),
            remark=item.remark,
            operator_user_id=item.operator_user_id,
            operator_name=user_name_map.get(item.operator_user_id),
            created_at=item.created_at,
        )
        for item in rows
    ]
