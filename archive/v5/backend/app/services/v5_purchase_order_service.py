from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.master_data import OilProduct, Warehouse
from app.models.user import User, UserRole
from app.models.v5_domain import (
    AgreementTemplate,
    AgreementTemplateVersion,
    Company,
    ContractExecutionLog,
    ContractStatus,
    FileAsset,
    InventoryBalance,
    InventoryMovement,
    InventoryMovementType,
    PurchaseContract,
    PurchaseContractItem,
    PurchaseOrderV5,
    PurchaseOrderV5Status,
    SalesContract,
    SalesInventoryReservation,
    SalesInventoryReservationStatus,
    SalesOrderV5,
    SalesOrderV5Status,
    TemplateStatus,
    TemplateType,
)
from app.schemas.v5_purchase_order import PurchaseOrderDetailOut, PurchaseOrderListItemOut
from app.services.file_storage_service import build_protected_file_url_by_key
from app.services.v5_delivery_instruction_service import generate_delivery_instruction_pdf
from app.services.v5_file_asset_service import ensure_file_asset, list_file_keys_by_link, replace_file_asset_links
from app.services.v5_sales_order_service import release_sales_inventory_reservation


OUTBOUND_QTY_LIMIT_RATIO = Decimal("1.10")


def _normalize_decimal(value: float, precision: str = "0.0000") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(precision))


def _build_tax_amounts(*, amount_tax_included: Decimal | None, tax_rate: Decimal | None) -> tuple[float | None, float | None]:
    if amount_tax_included is None or tax_rate is None:
        return None, None
    amount_tax_excluded = (amount_tax_included / (Decimal("1.0000") + tax_rate)).quantize(Decimal("0.01"))
    tax_amount = (amount_tax_included - amount_tax_excluded).quantize(Decimal("0.01"))
    return float(amount_tax_excluded), float(tax_amount)


def _validate_warehouse_outbound_qty(*, order_qty: Decimal, outbound_qty: Decimal) -> None:
    # BR-030：仓库一次出库不得低于订单数量，且不得超过订单数量的10%
    if outbound_qty < order_qty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="actual_outbound_qty_less_than_order_qty")
    if outbound_qty > order_qty * OUTBOUND_QTY_LIMIT_RATIO:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="actual_outbound_qty_exceeds_order_qty_limit")


def _require_company_bound(current_user: User) -> int:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_not_bound")
    return current_user.company_id


def _resolve_purchase_order_scope_filter(db: Session, current_user: User):
    if current_user.role == UserRole.SUPPLIER:
        return PurchaseOrderV5.supplier_company_id == _require_company_bound(current_user)
    if current_user.role == UserRole.WAREHOUSE:
        company_id = _require_company_bound(current_user)
        warehouse_ids = db.scalars(select(Warehouse.id).where(Warehouse.company_id == company_id)).all()
        if not warehouse_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="warehouse_company_not_bound")
        return PurchaseOrderV5.warehouse_id.in_(warehouse_ids)
    return None


def get_purchase_order_with_scope(db: Session, *, purchase_order_id: int, current_user: User) -> PurchaseOrderV5:
    query = select(PurchaseOrderV5).where(PurchaseOrderV5.id == purchase_order_id)
    scope_filter = _resolve_purchase_order_scope_filter(db, current_user)
    if scope_filter is not None:
        query = query.where(scope_filter)
    row = db.scalar(query)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="purchase_order_not_found")
    return row


def list_purchase_orders(
    db: Session,
    *,
    current_user: User,
    status_value: PurchaseOrderV5Status | None,
    pending_only: bool,
    from_date: date | None,
    to_date: date | None,
    page: int,
    page_size: int,
) -> list[PurchaseOrderV5]:
    query = select(PurchaseOrderV5).join(SalesOrderV5, SalesOrderV5.id == PurchaseOrderV5.sales_order_id)
    scope_filter = _resolve_purchase_order_scope_filter(db, current_user)
    if scope_filter is not None:
        query = query.where(scope_filter)
    if status_value is not None:
        query = query.where(PurchaseOrderV5.status == status_value)
    if pending_only:
        query = query.where(
            PurchaseOrderV5.status.in_(
                (
                    PurchaseOrderV5Status.PENDING_SUBMIT,
                    PurchaseOrderV5Status.SUPPLIER_PAYMENT_PENDING,
                    PurchaseOrderV5Status.SUPPLIER_REVIEW_PENDING,
                    PurchaseOrderV5Status.WAREHOUSE_PENDING,
                )
            )
        )
    if from_date is not None:
        query = query.where(SalesOrderV5.order_date >= from_date)
    if to_date is not None:
        query = query.where(SalesOrderV5.order_date <= to_date)
    query = query.order_by(PurchaseOrderV5.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(query).all()


def _require_purchase_contract(
    db: Session,
    *,
    purchase_contract_id: int,
    product_id: int,
) -> tuple[PurchaseContract, PurchaseContractItem]:
    contract = db.scalar(
        select(PurchaseContract).where(
            PurchaseContract.id == purchase_contract_id,
            PurchaseContract.status.in_((ContractStatus.EFFECTIVE, ContractStatus.PARTIALLY_EXECUTED)),
        )
    )
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="purchase_contract_not_found")
    if contract.pending_execution_qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_pending_qty_empty")

    item = db.scalar(
        select(PurchaseContractItem).where(
            PurchaseContractItem.purchase_contract_id == contract.id,
            PurchaseContractItem.product_id == product_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_product_not_match")
    return contract, item


def _require_delivery_template(
    db: Session,
    *,
    delivery_instruction_template_id: int,
) -> tuple[AgreementTemplate, AgreementTemplateVersion]:
    template = db.scalar(
        select(AgreementTemplate).where(
            AgreementTemplate.id == delivery_instruction_template_id,
            AgreementTemplate.template_type == TemplateType.DELIVERY_INSTRUCTION,
            AgreementTemplate.status == TemplateStatus.ENABLED,
        )
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="delivery_instruction_template_not_found")
    version = db.scalar(
        select(AgreementTemplateVersion).where(
            AgreementTemplateVersion.template_id == template.id,
            AgreementTemplateVersion.version_no == template.current_version_no,
        )
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delivery_instruction_template_version_not_found")
    return template, version


def _build_purchase_contract_snapshot(
    contract: PurchaseContract,
    item: PurchaseContractItem,
    *,
    buyer_company_name: str | None,
    supplier_company_name: str | None,
) -> dict[str, object]:
    return {
        "purchase_contract_id": contract.id,
        "contract_no": contract.contract_no,
        "status": contract.status.value,
        "contract_business_direction": "采购",
        "counterparty_role_text": "卖方",
        "supplier_company_id": contract.supplier_company_id,
        "supplier_company_name": str(supplier_company_name or "").strip(),
        "counterparty_company_name": str(supplier_company_name or "").strip(),
        "buyer_company_name": str(buyer_company_name or "").strip(),
        "seller_company_name": str(supplier_company_name or "").strip(),
        "product_id": item.product_id,
        "unit_name": item.unit_name,
        "unit_price_tax_included": str(item.unit_price_tax_included),
        "pending_execution_qty": str(contract.pending_execution_qty),
    }


def _build_delivery_template_snapshot(template: AgreementTemplate, version: AgreementTemplateVersion) -> dict[str, object]:
    return {
        "template_id": template.id,
        "template_code": template.template_code,
        "template_name": template.template_name,
        "version_no": version.version_no,
        "template_title": version.template_title,
        "template_content_json": version.template_content_json,
    }


def _resolve_file_key(file_asset_id: int | None, db: Session) -> str | None:
    if file_asset_id is None:
        return None
    return db.scalar(select(FileAsset.file_key).where(FileAsset.id == file_asset_id))


def _resolve_file_name(file_asset_id: int | None, db: Session) -> str | None:
    if file_asset_id is None:
        return None
    return db.scalar(select(FileAsset.file_name).where(FileAsset.id == file_asset_id))


def _update_contract_execution(contract, executed_qty: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    before_executed_qty = contract.executed_qty
    before_pending_qty = contract.pending_execution_qty
    contract.executed_qty = (contract.executed_qty + executed_qty).quantize(Decimal("0.0000"))
    effective_qty = contract.effective_contract_qty
    pending_qty = (effective_qty - contract.executed_qty).quantize(Decimal("0.0000"))
    if pending_qty <= 0:
        contract.pending_execution_qty = Decimal("0.0000")
        contract.over_executed_qty = abs(min(pending_qty, Decimal("0.0000"))).quantize(Decimal("0.0000"))
        contract.status = ContractStatus.COMPLETED
    else:
        contract.pending_execution_qty = pending_qty
        contract.over_executed_qty = Decimal("0.0000")
        contract.status = ContractStatus.PARTIALLY_EXECUTED
    return before_executed_qty, contract.executed_qty, before_pending_qty, contract.pending_execution_qty


def _resolve_purchase_contract_signing_subject_name(
    *,
    contract_snapshot: dict[str, object] | None,
    supplier_company_name: str | None,
) -> str | None:
    seller_name = str((contract_snapshot or {}).get("seller_company_name") or "").strip()
    if seller_name:
        return seller_name
    snapshot_name = str((contract_snapshot or {}).get("supplier_company_name") or "").strip()
    if snapshot_name:
        return snapshot_name
    current_name = str(supplier_company_name or "").strip()
    return current_name or None


def _resolve_purchase_contract_buyer_name(
    *,
    contract_snapshot: dict[str, object] | None,
    operator_company_name: str | None,
) -> str | None:
    snapshot_name = str((contract_snapshot or {}).get("buyer_company_name") or "").strip()
    if snapshot_name:
        return snapshot_name
    current_name = str(operator_company_name or "").strip()
    return current_name or None


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


def _mark_sales_order_abnormal_closed(
    sales_order: SalesOrderV5,
    *,
    reason: str,
    current_user: User,
) -> None:
    now = datetime.now(UTC)
    sales_order.status = SalesOrderV5Status.ABNORMAL_CLOSED
    sales_order.closed_reason = reason
    sales_order.closed_by = current_user.id
    sales_order.closed_at = now


def submit_purchase_order(
    db: Session,
    *,
    purchase_order: PurchaseOrderV5,
    purchase_contract_id: int,
    delivery_instruction_template_id: int,
    confirm_snapshot: dict[str, object],
    confirm_acknowledged: bool,
    supplier_payment_voucher_file_keys: list[str],
    current_user: User,
) -> PurchaseOrderV5:
    if purchase_order.status != PurchaseOrderV5Status.PENDING_SUBMIT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_order_status_invalid")

    purchase_contract, purchase_contract_item = _require_purchase_contract(
        db,
        purchase_contract_id=purchase_contract_id,
        product_id=purchase_order.product_id,
    )
    template, template_version = _require_delivery_template(
        db,
        delivery_instruction_template_id=delivery_instruction_template_id,
    )
    sales_order = db.scalar(select(SalesOrderV5).where(SalesOrderV5.id == purchase_order.sales_order_id))
    if sales_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sales_order_not_found")
    supplier_company_name = db.scalar(select(Company.company_name).where(Company.id == purchase_contract.supplier_company_id)) or ""
    buyer_company_name = str((purchase_contract.variable_snapshot_json or {}).get("buyer_company_name") or "").strip()

    purchase_order.purchase_contract_id = purchase_contract.id
    purchase_order.purchase_contract_snapshot_json = _build_purchase_contract_snapshot(
        purchase_contract,
        purchase_contract_item,
        buyer_company_name=buyer_company_name,
        supplier_company_name=supplier_company_name,
    )
    purchase_order.supplier_company_id = purchase_contract.supplier_company_id
    purchase_order.unit_price_tax_included = purchase_contract_item.unit_price_tax_included
    purchase_order.amount_tax_included = (purchase_contract_item.unit_price_tax_included * purchase_order.qty_ton).quantize(
        Decimal("0.01")
    )
    purchase_order.confirm_snapshot_json = confirm_snapshot
    purchase_order.confirm_acknowledged = confirm_acknowledged
    purchase_order.delivery_instruction_template_id = template.id
    purchase_order.delivery_instruction_template_version_id = template_version.id
    purchase_order.delivery_instruction_template_snapshot_json = _build_delivery_template_snapshot(template, template_version)

    pdf_file_key = generate_delivery_instruction_pdf(
        db,
        purchase_order=purchase_order,
        sales_order=sales_order,
        template=template,
        template_version=template_version,
    )
    pdf_file_asset = ensure_file_asset(
        db,
        file_key=pdf_file_key,
        business_type="delivery_instruction_pdf",
        current_user=current_user,
        file_name=f"{purchase_order.purchase_order_no}-发货指令单.pdf",
    )
    purchase_order.delivery_instruction_pdf_file_id = pdf_file_asset.id
    # BR-078：付款凭证随提交同步保存，直接流转到供应商审核节点；支持多个凭证文件
    primary_file_asset = ensure_file_asset(
        db,
        file_key=supplier_payment_voucher_file_keys[0],
        business_type="supplier_payment_voucher",
        current_user=current_user,
    )
    purchase_order.supplier_payment_voucher_file_id = primary_file_asset.id
    # 将所有凭证文件（含主凭证）通过 FileAssetLink 关联到采购订单，便于后续查询
    all_file_asset_ids = [primary_file_asset.id]
    for extra_key in supplier_payment_voucher_file_keys[1:]:
        extra_asset = ensure_file_asset(
            db,
            file_key=extra_key,
            business_type="supplier_payment_voucher",
            current_user=current_user,
        )
        all_file_asset_ids.append(extra_asset.id)
    replace_file_asset_links(
        db,
        entity_type="PURCHASE_ORDER",
        entity_id=purchase_order.id,
        field_name="supplier_payment_vouchers",
        file_asset_ids=all_file_asset_ids,
    )
    purchase_order.supplier_paid_by = current_user.id
    purchase_order.supplier_paid_at = datetime.now(UTC)
    purchase_order.status = PurchaseOrderV5Status.SUPPLIER_REVIEW_PENDING
    purchase_order.contract_confirmed_by = current_user.id
    purchase_order.contract_confirmed_at = datetime.now(UTC)
    return purchase_order


def apply_supplier_payment(
    db: Session,
    *,
    purchase_order: PurchaseOrderV5,
    supplier_payment_voucher_file_key: str,
    current_user: User,
) -> PurchaseOrderV5:
    if purchase_order.status != PurchaseOrderV5Status.SUPPLIER_PAYMENT_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_order_status_invalid")
    file_asset = ensure_file_asset(
        db,
        file_key=supplier_payment_voucher_file_key,
        business_type="supplier_payment_voucher",
        current_user=current_user,
    )
    purchase_order.supplier_payment_voucher_file_id = file_asset.id
    purchase_order.status = PurchaseOrderV5Status.SUPPLIER_REVIEW_PENDING
    purchase_order.supplier_paid_by = current_user.id
    purchase_order.supplier_paid_at = datetime.now(UTC)
    return purchase_order


def apply_supplier_review(
    db: Session,
    *,
    purchase_order: PurchaseOrderV5,
    supplier_delivery_doc_file_key: str,
    current_user: User,
) -> tuple[PurchaseOrderV5, SalesOrderV5]:
    if purchase_order.status != PurchaseOrderV5Status.SUPPLIER_REVIEW_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_order_status_invalid")
    sales_order = db.scalar(select(SalesOrderV5).where(SalesOrderV5.id == purchase_order.sales_order_id))
    if sales_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sales_order_not_found")
    file_asset = ensure_file_asset(
        db,
        file_key=supplier_delivery_doc_file_key,
        business_type="supplier_delivery_doc",
        current_user=current_user,
    )
    purchase_order.supplier_delivery_doc_file_id = file_asset.id
    purchase_order.status = PurchaseOrderV5Status.WAREHOUSE_PENDING
    purchase_order.supplier_reviewed_by = current_user.id
    purchase_order.supplier_reviewed_at = datetime.now(UTC)
    sales_order.status = SalesOrderV5Status.READY_FOR_OUTBOUND
    return purchase_order, sales_order


def apply_warehouse_outbound(
    db: Session,
    *,
    purchase_order: PurchaseOrderV5,
    actual_outbound_qty: float,
    outbound_doc_file_key: str,
    current_user: User,
) -> tuple[PurchaseOrderV5, SalesOrderV5]:
    if purchase_order.status != PurchaseOrderV5Status.WAREHOUSE_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_order_status_invalid")
    sales_order = db.scalar(select(SalesOrderV5).where(SalesOrderV5.id == purchase_order.sales_order_id))
    if sales_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sales_order_not_found")
    if sales_order.status != SalesOrderV5Status.READY_FOR_OUTBOUND:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_order_status_invalid")

    outbound_qty = _normalize_decimal(actual_outbound_qty)
    _validate_warehouse_outbound_qty(order_qty=purchase_order.qty_ton, outbound_qty=outbound_qty)

    inventory_balance = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.warehouse_id == purchase_order.warehouse_id,
            InventoryBalance.product_id == purchase_order.product_id,
        )
    )
    if inventory_balance is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="inventory_balance_not_found")
    reservation = db.scalar(
        select(SalesInventoryReservation).where(
            SalesInventoryReservation.sales_order_id == sales_order.id,
            SalesInventoryReservation.status == SalesInventoryReservationStatus.ACTIVE,
        )
    )
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_reservation_not_found")
    reserved_qty = reservation.reserved_qty_ton
    extra_outbound_qty = max(outbound_qty - reserved_qty, Decimal("0.0000"))
    if (
        inventory_balance.on_hand_qty_ton < outbound_qty
        or inventory_balance.reserved_qty_ton < reserved_qty
        or inventory_balance.available_qty_ton < extra_outbound_qty
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="inventory_not_enough")

    outbound_doc_asset = ensure_file_asset(
        db,
        file_key=outbound_doc_file_key,
        business_type="outbound_doc",
        current_user=current_user,
    )
    before_on_hand = inventory_balance.on_hand_qty_ton
    before_reserved = inventory_balance.reserved_qty_ton
    inventory_balance.on_hand_qty_ton = (inventory_balance.on_hand_qty_ton - outbound_qty).quantize(Decimal("0.0000"))
    inventory_balance.reserved_qty_ton = (inventory_balance.reserved_qty_ton - reserved_qty).quantize(Decimal("0.0000"))
    inventory_balance.available_qty_ton = (inventory_balance.on_hand_qty_ton - inventory_balance.reserved_qty_ton).quantize(
        Decimal("0.0000")
    )
    inventory_balance.last_movement_at = datetime.now(UTC)
    reservation.status = SalesInventoryReservationStatus.CONSUMED
    reservation.released_reason = "仓库出库完成"
    reservation.released_at = datetime.now(UTC)
    sales_order.reserved_qty_ton = Decimal("0.0000")

    purchase_contract = None
    if purchase_order.purchase_contract_id is not None:
        purchase_contract = db.scalar(select(PurchaseContract).where(PurchaseContract.id == purchase_order.purchase_contract_id))
    sales_contract = db.scalar(select(SalesContract).where(SalesContract.id == sales_order.sales_contract_id))
    if sales_contract is None or purchase_contract is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contract_not_bound")

    sales_before_executed_qty, sales_after_executed_qty, sales_before_pending_qty, sales_after_pending_qty = _update_contract_execution(
        sales_contract,
        outbound_qty,
    )
    purchase_before_executed_qty, purchase_after_executed_qty, purchase_before_pending_qty, purchase_after_pending_qty = _update_contract_execution(
        purchase_contract,
        outbound_qty,
    )
    db.add(
        ContractExecutionLog(
            contract_type="SALES",
            contract_id=sales_contract.id,
            source_type="SALES_ORDER",
            source_id=sales_order.id,
            qty_ton=outbound_qty,
            before_executed_qty=sales_before_executed_qty,
            after_executed_qty=sales_after_executed_qty,
            before_pending_qty=sales_before_pending_qty,
            after_pending_qty=sales_after_pending_qty,
            operator_user_id=current_user.id,
        )
    )
    db.add(
        ContractExecutionLog(
            contract_type="PURCHASE",
            contract_id=purchase_contract.id,
            source_type="PURCHASE_ORDER",
            source_id=purchase_order.id,
            qty_ton=outbound_qty,
            before_executed_qty=purchase_before_executed_qty,
            after_executed_qty=purchase_after_executed_qty,
            before_pending_qty=purchase_before_pending_qty,
            after_pending_qty=purchase_after_pending_qty,
            operator_user_id=current_user.id,
        )
    )
    db.add(
        InventoryMovement(
            movement_no=f"MV-OUT-{purchase_order.purchase_order_no}",
            warehouse_id=purchase_order.warehouse_id,
            product_id=purchase_order.product_id,
            movement_type=InventoryMovementType.SALES_OUTBOUND,
            business_type="PURCHASE_ORDER",
            business_id=purchase_order.id,
            before_on_hand_qty_ton=before_on_hand,
            change_qty_ton=outbound_qty,
            after_on_hand_qty_ton=inventory_balance.on_hand_qty_ton,
            before_reserved_qty_ton=before_reserved,
            after_reserved_qty_ton=inventory_balance.reserved_qty_ton,
            operator_user_id=current_user.id,
            remark="仓库出库完成",
        )
    )

    purchase_order.outbound_doc_file_id = outbound_doc_asset.id
    purchase_order.actual_outbound_qty_ton = outbound_qty
    purchase_order.status = PurchaseOrderV5Status.COMPLETED
    purchase_order.warehouse_reviewed_by = current_user.id
    purchase_order.warehouse_reviewed_at = datetime.now(UTC)

    sales_order.actual_outbound_qty_ton = outbound_qty
    sales_order.status = SalesOrderV5Status.COMPLETED
    return purchase_order, sales_order


def abnormal_close_purchase_order(
    db: Session,
    *,
    purchase_order: PurchaseOrderV5,
    reason: str,
    current_user: User,
) -> tuple[PurchaseOrderV5, SalesOrderV5]:
    if purchase_order.status not in (
        PurchaseOrderV5Status.PENDING_SUBMIT,
        PurchaseOrderV5Status.SUPPLIER_PAYMENT_PENDING,
        PurchaseOrderV5Status.SUPPLIER_REVIEW_PENDING,
        PurchaseOrderV5Status.WAREHOUSE_PENDING,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_order_status_invalid")

    sales_order = db.scalar(select(SalesOrderV5).where(SalesOrderV5.id == purchase_order.sales_order_id))
    if sales_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sales_order_not_found")

    release_sales_inventory_reservation(
        db,
        sales_order=sales_order,
        current_user=current_user,
        reason=f"采购订单异常关闭释放库存：{reason}",
    )
    _mark_sales_order_abnormal_closed(
        sales_order,
        reason=reason,
        current_user=current_user,
    )
    _mark_purchase_order_abnormal_closed(
        purchase_order,
        reason=reason,
        current_user=current_user,
    )
    return purchase_order, sales_order


def _serialize_purchase_order_row(
    *,
    db: Session,
    purchase_order: PurchaseOrderV5,
    current_user: User,
    sales_order: SalesOrderV5,
    sales_order_no: str,
    purchase_contract_no: str | None,
    supplier_company_name: str | None,
    warehouse_name: str,
    product_name: str,
    delivery_instruction_template_name: str | None,
    customer_company_name: str | None,
    sales_contract_no: str | None,
    contract_item_tax_rate: Decimal | None,
) -> tuple[PurchaseOrderListItemOut, PurchaseOrderDetailOut]:
    delivery_instruction_pdf_file_key = _resolve_file_key(purchase_order.delivery_instruction_pdf_file_id, db)
    delivery_instruction_pdf_file_name = _resolve_file_name(purchase_order.delivery_instruction_pdf_file_id, db)
    supplier_payment_voucher_file_key = _resolve_file_key(purchase_order.supplier_payment_voucher_file_id, db)
    supplier_delivery_doc_file_key = _resolve_file_key(purchase_order.supplier_delivery_doc_file_id, db)
    supplier_delivery_doc_file_name = _resolve_file_name(purchase_order.supplier_delivery_doc_file_id, db)
    outbound_doc_file_key = _resolve_file_key(purchase_order.outbound_doc_file_id, db)
    outbound_doc_file_name = _resolve_file_name(purchase_order.outbound_doc_file_id, db)
    amount_tax_excluded, tax_amount = _build_tax_amounts(
        amount_tax_included=purchase_order.amount_tax_included,
        tax_rate=contract_item_tax_rate,
    )

    payload = {
        "id": purchase_order.id,
        "purchase_order_no": purchase_order.purchase_order_no,
        "order_date": sales_order.order_date,
        "sales_order_id": purchase_order.sales_order_id,
        "sales_order_no": sales_order_no,
        "purchase_contract_id": purchase_order.purchase_contract_id,
        "purchase_contract_no": purchase_contract_no,
        "buyer_company_name": _resolve_purchase_contract_buyer_name(
            contract_snapshot=purchase_order.purchase_contract_snapshot_json,
            operator_company_name=sales_order.operator_company_name_snapshot,
        ),
        "seller_company_name": supplier_company_name,
        "contract_signing_subject_name": _resolve_purchase_contract_signing_subject_name(
            contract_snapshot=purchase_order.purchase_contract_snapshot_json,
            supplier_company_name=supplier_company_name,
        ),
        "supplier_company_id": purchase_order.supplier_company_id,
        "supplier_company_name": supplier_company_name,
        "warehouse_id": purchase_order.warehouse_id,
        "warehouse_name": warehouse_name,
        "product_id": purchase_order.product_id,
        "product_name": product_name,
        "qty_ton": float(purchase_order.qty_ton),
        "unit_price_tax_included": float(purchase_order.unit_price_tax_included) if purchase_order.unit_price_tax_included is not None else None,
        "amount_tax_included": float(purchase_order.amount_tax_included) if purchase_order.amount_tax_included is not None else None,
        "amount_tax_excluded": amount_tax_excluded,
        "tax_amount": tax_amount,
        "status": purchase_order.status,
        "actual_outbound_qty_ton": float(purchase_order.actual_outbound_qty_ton),
        "delivery_instruction_template_id": purchase_order.delivery_instruction_template_id,
        "delivery_instruction_template_name": delivery_instruction_template_name,
        "delivery_instruction_pdf_file_key": delivery_instruction_pdf_file_key,
        "delivery_instruction_pdf_file_url": build_protected_file_url_by_key(delivery_instruction_pdf_file_key) if delivery_instruction_pdf_file_key else None,
        "delivery_instruction_pdf_file_name": delivery_instruction_pdf_file_name,
        "supplier_payment_voucher_file_key": supplier_payment_voucher_file_key,
        "supplier_payment_voucher_file_url": build_protected_file_url_by_key(supplier_payment_voucher_file_key) if supplier_payment_voucher_file_key else None,
        "supplier_delivery_doc_file_key": supplier_delivery_doc_file_key,
        "supplier_delivery_doc_file_url": build_protected_file_url_by_key(supplier_delivery_doc_file_key) if supplier_delivery_doc_file_key else None,
        "supplier_delivery_doc_file_name": supplier_delivery_doc_file_name,
        "outbound_doc_file_key": outbound_doc_file_key,
        "outbound_doc_file_url": build_protected_file_url_by_key(outbound_doc_file_key) if outbound_doc_file_key else None,
        "outbound_doc_file_name": outbound_doc_file_name,
        "closed_reason": purchase_order.closed_reason,
        "closed_by": purchase_order.closed_by,
        "closed_at": purchase_order.closed_at,
        "created_at": purchase_order.created_at,
        "updated_at": purchase_order.updated_at,
        "sales_order_status": sales_order.status.value,
        "customer_company_id": sales_order.customer_company_id,
        "customer_company_name": customer_company_name,
        "sales_contract_id": sales_order.sales_contract_id,
        "sales_contract_no": sales_contract_no,
        "confirm_snapshot": purchase_order.confirm_snapshot_json,
        "confirm_acknowledged": purchase_order.confirm_acknowledged,
        "purchase_contract_snapshot": purchase_order.purchase_contract_snapshot_json,
        "delivery_instruction_template_snapshot": purchase_order.delivery_instruction_template_snapshot_json,
        "contract_confirmed_by": purchase_order.contract_confirmed_by,
        "contract_confirmed_at": purchase_order.contract_confirmed_at,
        "supplier_paid_by": purchase_order.supplier_paid_by,
        "supplier_paid_at": purchase_order.supplier_paid_at,
        "supplier_reviewed_by": purchase_order.supplier_reviewed_by,
        "supplier_reviewed_at": purchase_order.supplier_reviewed_at,
        "warehouse_reviewed_by": purchase_order.warehouse_reviewed_by,
        "warehouse_reviewed_at": purchase_order.warehouse_reviewed_at,
    }

    if current_user.role in {UserRole.SUPPLIER, UserRole.WAREHOUSE}:
        payload["customer_company_id"] = None
        payload["customer_company_name"] = None
        payload["sales_contract_id"] = None
        payload["sales_contract_no"] = None
    if current_user.role in {UserRole.SUPPLIER, UserRole.WAREHOUSE}:
        payload["unit_price_tax_included"] = None
        payload["amount_tax_included"] = None
        payload["amount_tax_excluded"] = None
        payload["tax_amount"] = None
        payload["supplier_payment_voucher_file_key"] = None
        payload["supplier_payment_voucher_file_url"] = None

    # 查询额外付款凭证文件列表（通过 FileAssetLink 关联，包含主凭证在内的全部文件）
    extra_voucher_keys = list_file_keys_by_link(
        db,
        entity_type="PURCHASE_ORDER",
        entity_id=purchase_order.id,
        field_name="supplier_payment_vouchers",
    )
    if extra_voucher_keys and current_user.role not in {UserRole.SUPPLIER, UserRole.WAREHOUSE}:
        payload["supplier_payment_voucher_attachments"] = [
            {"file_key": k, "file_url": build_protected_file_url_by_key(k)}
            for k in extra_voucher_keys
        ]
    else:
        payload["supplier_payment_voucher_attachments"] = None

    return PurchaseOrderListItemOut(**payload), PurchaseOrderDetailOut(**payload)


def serialize_purchase_order_list(db: Session, *, purchase_orders: list[PurchaseOrderV5], current_user: User) -> list[PurchaseOrderListItemOut]:
    if not purchase_orders:
        return []
    sales_order_ids = {item.sales_order_id for item in purchase_orders}
    purchase_contract_ids = {item.purchase_contract_id for item in purchase_orders if item.purchase_contract_id is not None}
    supplier_company_ids = {item.supplier_company_id for item in purchase_orders if item.supplier_company_id is not None}
    warehouse_ids = {item.warehouse_id for item in purchase_orders}
    product_ids = {item.product_id for item in purchase_orders}
    template_ids = {item.delivery_instruction_template_id for item in purchase_orders if item.delivery_instruction_template_id is not None}
    purchase_contract_item_tax_rate_map = {
        (row.purchase_contract_id, row.product_id): row.tax_rate
        for row in db.scalars(
            select(PurchaseContractItem).where(
                PurchaseContractItem.purchase_contract_id.in_(purchase_contract_ids),
                PurchaseContractItem.product_id.in_(product_ids),
            )
        ).all()
    } if purchase_contract_ids else {}

    sales_orders = {row.id: row for row in db.scalars(select(SalesOrderV5).where(SalesOrderV5.id.in_(sales_order_ids))).all()}
    customer_company_ids = {item.customer_company_id for item in sales_orders.values()}
    customer_name_map = dict(db.execute(select(Company.id, Company.company_name).where(Company.id.in_(customer_company_ids))).all())
    purchase_contract_no_map = dict(db.execute(select(PurchaseContract.id, PurchaseContract.contract_no).where(PurchaseContract.id.in_(purchase_contract_ids))).all())
    supplier_name_map = dict(db.execute(select(Company.id, Company.company_name).where(Company.id.in_(supplier_company_ids))).all())
    warehouse_name_map = dict(db.execute(select(Warehouse.id, Warehouse.name).where(Warehouse.id.in_(warehouse_ids))).all())
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(product_ids))).all())
    template_name_map = dict(db.execute(select(AgreementTemplate.id, AgreementTemplate.template_name).where(AgreementTemplate.id.in_(template_ids))).all())
    sales_contract_no_map = dict(db.execute(select(SalesContract.id, SalesContract.contract_no).where(SalesContract.id.in_({item.sales_contract_id for item in sales_orders.values()}))).all())

    result: list[PurchaseOrderListItemOut] = []
    for item in purchase_orders:
        sales_order = sales_orders[item.sales_order_id]
        list_item, _ = _serialize_purchase_order_row(
            db=db,
            purchase_order=item,
            current_user=current_user,
            sales_order=sales_order,
            sales_order_no=sales_order.sales_order_no,
            purchase_contract_no=purchase_contract_no_map.get(item.purchase_contract_id),
            supplier_company_name=supplier_name_map.get(item.supplier_company_id),
            warehouse_name=warehouse_name_map.get(item.warehouse_id, ""),
            product_name=product_name_map.get(item.product_id, ""),
            delivery_instruction_template_name=template_name_map.get(item.delivery_instruction_template_id),
            customer_company_name=customer_name_map.get(sales_order.customer_company_id),
            sales_contract_no=sales_contract_no_map.get(sales_order.sales_contract_id),
            contract_item_tax_rate=purchase_contract_item_tax_rate_map.get((item.purchase_contract_id, item.product_id)),
        )
        result.append(list_item)
    return result


def serialize_purchase_order_detail(db: Session, *, purchase_order: PurchaseOrderV5, current_user: User) -> PurchaseOrderDetailOut:
    sales_order = db.scalar(select(SalesOrderV5).where(SalesOrderV5.id == purchase_order.sales_order_id))
    if sales_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sales_order_not_found")
    customer_company_name = db.scalar(select(Company.company_name).where(Company.id == sales_order.customer_company_id))
    supplier_company_name = None
    if purchase_order.supplier_company_id is not None:
        supplier_company_name = db.scalar(select(Company.company_name).where(Company.id == purchase_order.supplier_company_id))
    warehouse_name = db.scalar(select(Warehouse.name).where(Warehouse.id == purchase_order.warehouse_id)) or ""
    product_name = db.scalar(select(OilProduct.name).where(OilProduct.id == purchase_order.product_id)) or ""
    purchase_contract_no = None
    if purchase_order.purchase_contract_id is not None:
        purchase_contract_no = db.scalar(select(PurchaseContract.contract_no).where(PurchaseContract.id == purchase_order.purchase_contract_id))
    template_name = None
    if purchase_order.delivery_instruction_template_id is not None:
        template_name = db.scalar(select(AgreementTemplate.template_name).where(AgreementTemplate.id == purchase_order.delivery_instruction_template_id))
    sales_contract_no = db.scalar(select(SalesContract.contract_no).where(SalesContract.id == sales_order.sales_contract_id))
    contract_item_tax_rate = None
    if purchase_order.purchase_contract_id is not None:
        contract_item_tax_rate = db.scalar(
            select(PurchaseContractItem.tax_rate).where(
                PurchaseContractItem.purchase_contract_id == purchase_order.purchase_contract_id,
                PurchaseContractItem.product_id == purchase_order.product_id,
            )
        )
    _, detail = _serialize_purchase_order_row(
        db=db,
        purchase_order=purchase_order,
        current_user=current_user,
        sales_order=sales_order,
        sales_order_no=sales_order.sales_order_no,
        purchase_contract_no=purchase_contract_no,
        supplier_company_name=supplier_company_name,
        warehouse_name=warehouse_name,
        product_name=product_name,
        delivery_instruction_template_name=template_name,
        customer_company_name=customer_company_name,
        sales_contract_no=sales_contract_no,
        contract_item_tax_rate=contract_item_tax_rate,
    )
    return detail
