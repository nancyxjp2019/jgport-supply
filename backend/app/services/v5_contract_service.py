from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.master_data import OilProduct, Warehouse
from app.models.user import User, UserRole
from app.models.v5_domain import (
    AgreementTemplate,
    AgreementTemplateVersion,
    Company,
    CompanyType,
    ContractStatus,
    PurchaseContract,
    PurchaseContractItem,
    PurchaseOrderV5,
    PurchaseStockIn,
    PurchaseStockInSourceKind,
    PurchaseStockInStatus,
    SalesContract,
    SalesContractItem,
    SalesOrderV5,
    TemplateType,
)
from app.schemas.v5_contract import (
    ContractItemIn,
    ContractItemOut,
    PurchaseContractCreateRequest,
    PurchaseContractDetailOut,
    PurchaseContractListItemOut,
    PurchaseContractUpdateRequest,
    SalesContractCreateRequest,
    SalesContractDetailOut,
    SalesContractListItemOut,
    SalesContractUpdateRequest,
)
from app.services.v5_contract_pdf_service import generate_purchase_contract_pdf, generate_sales_contract_pdf
from app.services.file_storage_service import build_protected_file_url_by_key
from app.services.v5_file_asset_service import ensure_file_asset, list_file_keys_by_link, replace_file_asset_links
from app.services.v5_inventory_service import build_purchase_stock_in_no


_EDITABLE_CONTRACT_STATUSES = (ContractStatus.DRAFT, ContractStatus.PENDING_EFFECTIVE)
_VOIDABLE_CONTRACT_STATUSES = (ContractStatus.DRAFT, ContractStatus.PENDING_EFFECTIVE)


def _normalize_decimal(value: float, precision: str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(precision))


def _require_company_bound(current_user: User) -> int:
    if current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_not_bound")
    return current_user.company_id


def _apply_sales_contract_scope(query, *, current_user: User):
    if current_user.role == UserRole.CUSTOMER:
        return query.where(SalesContract.customer_company_id == _require_company_bound(current_user))
    return query


def _apply_purchase_contract_scope(query, *, current_user: User):
    if current_user.role == UserRole.SUPPLIER:
        return query.where(PurchaseContract.supplier_company_id == _require_company_bound(current_user))
    return query


def _get_template(
    db: Session,
    *,
    template_id: int,
    template_type: TemplateType,
) -> tuple[AgreementTemplate, AgreementTemplateVersion]:
    template = db.scalar(
        select(AgreementTemplate).where(
            AgreementTemplate.id == template_id,
            AgreementTemplate.template_type == template_type,
        )
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="contract_template_not_found")
    version = db.scalar(
        select(AgreementTemplateVersion).where(
            AgreementTemplateVersion.template_id == template.id,
            AgreementTemplateVersion.version_no == template.current_version_no,
        )
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contract_template_version_not_found")
    return template, version


def _get_company(
    db: Session,
    *,
    company_id: int,
    company_type: CompanyType,
) -> Company:
    row = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.company_type == company_type,
            Company.is_active.is_(True),
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_not_found")
    return row


def _resolve_operator_company_snapshot(db: Session, *, current_user: User) -> tuple[int | None, str]:
    if current_user.company_id is not None:
        company = db.scalar(
            select(Company).where(
                Company.id == current_user.company_id,
                Company.company_type == CompanyType.OPERATOR,
                Company.is_active.is_(True),
            )
        )
        if company is not None:
            return company.id, company.company_name
    operator_companies = db.scalars(
        select(Company).where(
            Company.company_type == CompanyType.OPERATOR,
            Company.is_active.is_(True),
        )
    ).all()
    if len(operator_companies) == 1:
        return operator_companies[0].id, operator_companies[0].company_name
    return None, ""


def _get_warehouse(db: Session, *, warehouse_id: int) -> Warehouse:
    row = db.scalar(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.is_active.is_(True)))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="warehouse_not_found")
    return row


def _parse_snapshot_warehouse_id(snapshot: dict[str, object] | None) -> int:
    raw_value = (snapshot or {}).get("warehouse_id")
    if raw_value in (None, ""):
        return 0
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return 0


def _resolve_purchase_contract_snapshot_warehouse(db: Session, *, snapshot: dict[str, object] | None) -> Warehouse | None:
    warehouse_id = _parse_snapshot_warehouse_id(snapshot)
    if warehouse_id > 0:
        return _get_warehouse(db, warehouse_id=warehouse_id)
    warehouse_name = str((snapshot or {}).get("warehouse_name") or "").strip()
    if not warehouse_name:
        return None
    return db.scalar(
        select(Warehouse).where(
            Warehouse.name == warehouse_name,
            Warehouse.is_active.is_(True),
        )
    )


def _validate_contract_items(
    db: Session,
    *,
    items: list[ContractItemIn],
) -> list[tuple[OilProduct, Decimal, Decimal, Decimal]]:
    seen_product_ids: set[int] = set()
    normalized_items: list[tuple[OilProduct, Decimal, Decimal, Decimal]] = []
    for item in items:
        if item.product_id in seen_product_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contract_product_duplicated")
        seen_product_ids.add(item.product_id)
        product = db.scalar(select(OilProduct).where(OilProduct.id == item.product_id, OilProduct.is_active.is_(True)))
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product_not_found")
        qty_ton = _normalize_decimal(item.qty_ton, "0.0000")
        tax_rate = _normalize_decimal(item.tax_rate, "0.0000")
        unit_price_tax_included = _normalize_decimal(item.unit_price_tax_included, "0.01")
        normalized_items.append((product, qty_ton, tax_rate, unit_price_tax_included))
    return normalized_items


def _build_item_amounts(
    *,
    qty_ton: Decimal,
    tax_rate: Decimal,
    unit_price_tax_included: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    amount_tax_included = (qty_ton * unit_price_tax_included).quantize(Decimal("0.01"))
    amount_tax_excluded = (amount_tax_included / (Decimal("1.0000") + tax_rate)).quantize(Decimal("0.01"))
    tax_amount = (amount_tax_included - amount_tax_excluded).quantize(Decimal("0.01"))
    return amount_tax_included, amount_tax_excluded, tax_amount


def _decimal_to_text(value: Decimal, precision: str) -> str:
    return format(value.quantize(Decimal(precision)), "f")


def _money_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), ",.2f")


def _percent_text(value: Decimal) -> str:
    text = format((value * Decimal("100")).quantize(Decimal("0.01")), "f").rstrip("0").rstrip(".")
    return f"{text}%"


def _build_contract_template_snapshot(
    *,
    template: AgreementTemplate,
    version: AgreementTemplateVersion,
    warehouse: Warehouse | None = None,
) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "template_id": template.id,
        "template_type": template.template_type.value if hasattr(template.template_type, "value") else str(template.template_type),
        "template_name": template.template_name,
        "template_title": version.template_title,
        "template_content_json": version.template_content_json or {},
        "placeholder_schema_json": version.placeholder_schema_json or {},
        "render_config_json": version.render_config_json or {},
    }
    if warehouse is not None:
        snapshot["warehouse_id"] = warehouse.id
        snapshot["warehouse_name"] = warehouse.name
    return snapshot


def _prepare_contract_items(
    db: Session,
    *,
    items: list[ContractItemIn],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    normalized_items = _validate_contract_items(db, items=items)
    prepared_items: list[dict[str, object]] = []
    product_names: list[str] = []
    total_qty = Decimal("0.0000")
    total_amount_tax_included = Decimal("0.00")
    total_amount_tax_excluded = Decimal("0.00")
    total_tax_amount = Decimal("0.00")
    for product, qty_ton, tax_rate, unit_price_tax_included in normalized_items:
        amount_tax_included, amount_tax_excluded, tax_amount = _build_item_amounts(
            qty_ton=qty_ton,
            tax_rate=tax_rate,
            unit_price_tax_included=unit_price_tax_included,
        )
        prepared_items.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "unit_name": product.unit_name or "吨",
                "qty_ton": qty_ton,
                "tax_rate": tax_rate,
                "unit_price_tax_included": unit_price_tax_included,
                "amount_tax_included": amount_tax_included,
                "amount_tax_excluded": amount_tax_excluded,
                "tax_amount": tax_amount,
            }
        )
        if product.name and product.name not in product_names:
            product_names.append(product.name)
        total_qty = (total_qty + qty_ton).quantize(Decimal("0.0000"))
        total_amount_tax_included = (total_amount_tax_included + amount_tax_included).quantize(Decimal("0.01"))
        total_amount_tax_excluded = (total_amount_tax_excluded + amount_tax_excluded).quantize(Decimal("0.01"))
        total_tax_amount = (total_tax_amount + tax_amount).quantize(Decimal("0.01"))
    return prepared_items, {
        "product_names": product_names,
        "item_count": len(prepared_items),
        "total_qty": total_qty,
        "total_amount_tax_included": total_amount_tax_included,
        "total_amount_tax_excluded": total_amount_tax_excluded,
        "total_tax_amount": total_tax_amount,
    }


def _prepare_existing_sales_contract_items(
    db: Session,
    *,
    contract: SalesContract,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows = db.scalars(select(SalesContractItem).where(SalesContractItem.sales_contract_id == contract.id).order_by(SalesContractItem.id.asc())).all()
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_({item.product_id for item in rows}))).all()) if rows else {}
    prepared_items = [
        {
            "product_id": item.product_id,
            "product_name": product_name_map.get(item.product_id, ""),
            "unit_name": item.unit_name,
            "qty_ton": item.qty_ton,
            "tax_rate": item.tax_rate,
            "unit_price_tax_included": item.unit_price_tax_included,
            "amount_tax_included": item.amount_tax_included,
            "amount_tax_excluded": item.amount_tax_excluded,
            "tax_amount": item.tax_amount,
        }
        for item in rows
    ]
    return _summarize_prepared_contract_items(prepared_items)


def _prepare_existing_purchase_contract_items(
    db: Session,
    *,
    contract: PurchaseContract,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows = db.scalars(select(PurchaseContractItem).where(PurchaseContractItem.purchase_contract_id == contract.id).order_by(PurchaseContractItem.id.asc())).all()
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_({item.product_id for item in rows}))).all()) if rows else {}
    prepared_items = [
        {
            "product_id": item.product_id,
            "product_name": product_name_map.get(item.product_id, ""),
            "unit_name": item.unit_name,
            "qty_ton": item.qty_ton,
            "tax_rate": item.tax_rate,
            "unit_price_tax_included": item.unit_price_tax_included,
            "amount_tax_included": item.amount_tax_included,
            "amount_tax_excluded": item.amount_tax_excluded,
            "tax_amount": item.tax_amount,
        }
        for item in rows
    ]
    return _summarize_prepared_contract_items(prepared_items)


def _summarize_prepared_contract_items(prepared_items: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    product_names: list[str] = []
    total_qty = Decimal("0.0000")
    total_amount_tax_included = Decimal("0.00")
    total_amount_tax_excluded = Decimal("0.00")
    total_tax_amount = Decimal("0.00")
    for item in prepared_items:
        product_name = str(item.get("product_name") or "").strip()
        if product_name and product_name not in product_names:
            product_names.append(product_name)
        total_qty = (total_qty + Decimal(str(item.get("qty_ton") or 0))).quantize(Decimal("0.0000"))
        total_amount_tax_included = (total_amount_tax_included + Decimal(str(item.get("amount_tax_included") or 0))).quantize(Decimal("0.01"))
        total_amount_tax_excluded = (total_amount_tax_excluded + Decimal(str(item.get("amount_tax_excluded") or 0))).quantize(Decimal("0.01"))
        total_tax_amount = (total_tax_amount + Decimal(str(item.get("tax_amount") or 0))).quantize(Decimal("0.01"))
    return prepared_items, {
        "product_names": product_names,
        "item_count": len(prepared_items),
        "total_qty": total_qty,
        "total_amount_tax_included": total_amount_tax_included,
        "total_amount_tax_excluded": total_amount_tax_excluded,
        "total_tax_amount": total_tax_amount,
    }


def _build_contract_item_summary(prepared_items: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for index, item in enumerate(prepared_items, start=1):
        lines.append(
            "；".join(
                [
                    f"{index}.{item.get('product_name') or '-'}",
                    f"数量{_decimal_to_text(Decimal(str(item.get('qty_ton') or 0)), '0.0000')}吨",
                    f"税率{_percent_text(Decimal(str(item.get('tax_rate') or 0)))}",
                    f"含税单价{_money_text(Decimal(str(item.get('unit_price_tax_included') or 0)))}元",
                    f"含税金额{_money_text(Decimal(str(item.get('amount_tax_included') or 0)))}元",
                ]
            )
        )
    return "\n".join(lines)


def _build_contract_variable_snapshot(
    *,
    contract_no: str,
    contract_date,
    deposit_rate: Decimal,
    our_company_name: str | None,
    company_name: str | None,
    warehouse_name: str | None,
    prepared_items: list[dict[str, object]],
    item_metrics: dict[str, object],
    company_role: str,
) -> dict[str, object]:
    total_qty = Decimal(str(item_metrics.get("total_qty") or 0)).quantize(Decimal("0.0000"))
    total_amount_tax_included = Decimal(str(item_metrics.get("total_amount_tax_included") or 0)).quantize(Decimal("0.01"))
    total_amount_tax_excluded = Decimal(str(item_metrics.get("total_amount_tax_excluded") or 0)).quantize(Decimal("0.01"))
    total_tax_amount = Decimal(str(item_metrics.get("total_tax_amount") or 0)).quantize(Decimal("0.01"))
    deposit_amount = (total_amount_tax_included * deposit_rate).quantize(Decimal("0.01"))
    product_names = [str(item).strip() for item in item_metrics.get("product_names") or [] if str(item).strip()]
    product_name_text = "、".join(product_names)
    first_item = prepared_items[0] if prepared_items else {}
    snapshot: dict[str, object] = {
        "contract_no": contract_no,
        "contract_date": contract_date.isoformat(),
        "contract_date_text": contract_date.isoformat(),
        "our_company_name": our_company_name or "",
        "company_name": company_name or "",
        "contract_business_direction": "销售" if company_role == "customer" else "采购",
        "warehouse_name": warehouse_name or "",
        "product_name": product_name_text,
        "product_names": product_name_text,
        "qty_ton": _decimal_to_text(total_qty, "0.0000"),
        "contract_qty_ton": _decimal_to_text(total_qty, "0.0000"),
        "total_qty_ton": _decimal_to_text(total_qty, "0.0000"),
        "base_contract_qty": _decimal_to_text(total_qty, "0.0000"),
        "amount_tax_included": _money_text(total_amount_tax_included),
        "contract_amount_tax_included": _money_text(total_amount_tax_included),
        "total_amount_tax_included": _money_text(total_amount_tax_included),
        "amount_tax_excluded": _money_text(total_amount_tax_excluded),
        "total_amount_tax_excluded": _money_text(total_amount_tax_excluded),
        "tax_amount": _money_text(total_tax_amount),
        "total_tax_amount": _money_text(total_tax_amount),
        "deposit_rate": _percent_text(deposit_rate),
        "deposit_rate_text": _percent_text(deposit_rate),
        "deposit_amount": _money_text(deposit_amount),
        "item_count": int(item_metrics.get("item_count") or 0),
        "item_summary": _build_contract_item_summary(prepared_items),
        "unit_price_tax_included": _money_text(Decimal(str(first_item.get("unit_price_tax_included") or 0)))
        if len(prepared_items) == 1
        else "详见合同条目",
        "tax_rate": _percent_text(Decimal(str(first_item.get("tax_rate") or 0))) if len(prepared_items) == 1 else "详见合同条目",
        "tax_rate_text": _percent_text(Decimal(str(first_item.get("tax_rate") or 0))) if len(prepared_items) == 1 else "详见合同条目",
        "counterparty_company_name": company_name or "",
    }
    if company_role == "customer":
        snapshot["our_role_text"] = "卖方"
        snapshot["counterparty_role_text"] = "买方"
        snapshot["buyer_company_name"] = company_name or ""
        snapshot["seller_company_name"] = our_company_name or ""
        snapshot["customer_company_name"] = company_name or ""
        snapshot["customer_name"] = company_name or ""
    else:
        snapshot["our_role_text"] = "买方"
        snapshot["counterparty_role_text"] = "卖方"
        snapshot["buyer_company_name"] = our_company_name or ""
        snapshot["seller_company_name"] = company_name or ""
        snapshot["supplier_company_name"] = company_name or ""
        snapshot["supplier_name"] = company_name or ""
    return snapshot


def _rebuild_sales_contract_items(
    db: Session,
    *,
    contract: SalesContract,
    items: list[ContractItemIn],
) -> None:
    prepared_items, item_metrics = _prepare_contract_items(db, items=items)
    db.execute(delete(SalesContractItem).where(SalesContractItem.sales_contract_id == contract.id))
    for item in prepared_items:
        db.add(
            SalesContractItem(
                sales_contract_id=contract.id,
                product_id=int(item["product_id"]),
                qty_ton=item["qty_ton"],
                unit_name=str(item["unit_name"]),
                tax_rate=item["tax_rate"],
                unit_price_tax_included=item["unit_price_tax_included"],
                amount_tax_included=item["amount_tax_included"],
                amount_tax_excluded=item["amount_tax_excluded"],
                tax_amount=item["tax_amount"],
            )
        )
    total_qty = Decimal(str(item_metrics["total_qty"]))
    total_amount = Decimal(str(item_metrics["total_amount_tax_included"]))
    contract.base_contract_qty = total_qty
    contract.effective_contract_qty = total_qty
    contract.pending_execution_qty = total_qty
    contract.over_executed_qty = Decimal("0.0000")
    contract.deposit_amount = (total_amount * contract.deposit_rate).quantize(Decimal("0.01"))


def _rebuild_purchase_contract_items(
    db: Session,
    *,
    contract: PurchaseContract,
    items: list[ContractItemIn],
) -> None:
    prepared_items, item_metrics = _prepare_contract_items(db, items=items)
    db.execute(delete(PurchaseContractItem).where(PurchaseContractItem.purchase_contract_id == contract.id))
    for item in prepared_items:
        db.add(
            PurchaseContractItem(
                purchase_contract_id=contract.id,
                product_id=int(item["product_id"]),
                qty_ton=item["qty_ton"],
                unit_name=str(item["unit_name"]),
                tax_rate=item["tax_rate"],
                unit_price_tax_included=item["unit_price_tax_included"],
                amount_tax_included=item["amount_tax_included"],
                amount_tax_excluded=item["amount_tax_excluded"],
                tax_amount=item["tax_amount"],
            )
        )
    total_qty = Decimal(str(item_metrics["total_qty"]))
    total_amount = Decimal(str(item_metrics["total_amount_tax_included"]))
    contract.base_contract_qty = total_qty
    contract.effective_contract_qty = total_qty
    contract.pending_execution_qty = total_qty
    contract.pending_stock_in_qty = total_qty
    contract.over_executed_qty = Decimal("0.0000")
    contract.deposit_amount = (total_amount * contract.deposit_rate).quantize(Decimal("0.01"))


def list_sales_contracts(
    db: Session,
    *,
    current_user: User,
    status_value: ContractStatus | None,
    page: int,
    page_size: int,
) -> list[SalesContract]:
    query = _apply_sales_contract_scope(select(SalesContract), current_user=current_user)
    if status_value is not None:
        query = query.where(SalesContract.status == status_value)
    query = query.order_by(SalesContract.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(query).all()


def list_purchase_contracts(
    db: Session,
    *,
    current_user: User,
    status_value: ContractStatus | None,
    page: int,
    page_size: int,
) -> list[PurchaseContract]:
    query = _apply_purchase_contract_scope(select(PurchaseContract), current_user=current_user)
    if status_value is not None:
        query = query.where(PurchaseContract.status == status_value)
    query = query.order_by(PurchaseContract.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(query).all()


def get_sales_contract(db: Session, *, contract_id: int, current_user: User | None = None) -> SalesContract:
    query = select(SalesContract).where(SalesContract.id == contract_id)
    if current_user is not None:
        query = _apply_sales_contract_scope(query, current_user=current_user)
    row = db.scalar(query)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sales_contract_not_found")
    return row


def get_purchase_contract(db: Session, *, contract_id: int, current_user: User | None = None) -> PurchaseContract:
    query = select(PurchaseContract).where(PurchaseContract.id == contract_id)
    if current_user is not None:
        query = _apply_purchase_contract_scope(query, current_user=current_user)
    row = db.scalar(query)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="purchase_contract_not_found")
    return row


def create_sales_contract(db: Session, *, payload: SalesContractCreateRequest, current_user: User) -> SalesContract:
    existing = db.scalar(select(SalesContract).where(SalesContract.contract_no == payload.contract_no))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="sales_contract_no_exists")
    customer_company = _get_company(db, company_id=payload.customer_company_id, company_type=CompanyType.CUSTOMER)
    template, version = _get_template(db, template_id=payload.template_id, template_type=TemplateType.SALES_CONTRACT)
    prepared_items, item_metrics = _prepare_contract_items(db, items=payload.items)
    deposit_rate = _normalize_decimal(payload.deposit_rate, "0.0000")
    _our_company_id, our_company_name = _resolve_operator_company_snapshot(db, current_user=current_user)
    contract = SalesContract(
        contract_no=payload.contract_no,
        customer_company_id=customer_company.id,
        template_id=template.id,
        template_version_id=version.id,
        template_snapshot_json=_build_contract_template_snapshot(template=template, version=version),
        variable_snapshot_json=_build_contract_variable_snapshot(
            contract_no=payload.contract_no,
            contract_date=payload.contract_date,
            deposit_rate=deposit_rate,
            our_company_name=our_company_name,
            company_name=customer_company.company_name,
            warehouse_name=None,
            prepared_items=prepared_items,
            item_metrics=item_metrics,
            company_role="customer",
        ),
        contract_date=payload.contract_date,
        deposit_rate=deposit_rate,
        status=ContractStatus.DRAFT,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(contract)
    db.flush()
    _rebuild_sales_contract_items(db, contract=contract, items=payload.items)
    return contract


def create_purchase_contract(db: Session, *, payload: PurchaseContractCreateRequest, current_user: User) -> PurchaseContract:
    existing = db.scalar(select(PurchaseContract).where(PurchaseContract.contract_no == payload.contract_no))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="purchase_contract_no_exists")
    supplier_company = _get_company(db, company_id=payload.supplier_company_id, company_type=CompanyType.SUPPLIER)
    warehouse = _get_warehouse(db, warehouse_id=payload.warehouse_id)
    template, version = _get_template(db, template_id=payload.template_id, template_type=TemplateType.PURCHASE_CONTRACT)
    prepared_items, item_metrics = _prepare_contract_items(db, items=payload.items)
    deposit_rate = _normalize_decimal(payload.deposit_rate, "0.0000")
    _our_company_id, our_company_name = _resolve_operator_company_snapshot(db, current_user=current_user)
    contract = PurchaseContract(
        contract_no=payload.contract_no,
        supplier_company_id=supplier_company.id,
        template_id=template.id,
        template_version_id=version.id,
        template_snapshot_json=_build_contract_template_snapshot(template=template, version=version, warehouse=warehouse),
        variable_snapshot_json=_build_contract_variable_snapshot(
            contract_no=payload.contract_no,
            contract_date=payload.contract_date,
            deposit_rate=deposit_rate,
            our_company_name=our_company_name,
            company_name=supplier_company.company_name,
            warehouse_name=warehouse.name,
            prepared_items=prepared_items,
            item_metrics=item_metrics,
            company_role="supplier",
        ),
        contract_date=payload.contract_date,
        deposit_rate=deposit_rate,
        status=ContractStatus.DRAFT,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(contract)
    db.flush()
    _rebuild_purchase_contract_items(db, contract=contract, items=payload.items)
    return contract


def update_sales_contract(db: Session, *, contract: SalesContract, payload: SalesContractUpdateRequest, current_user: User) -> SalesContract:
    if contract.status not in _EDITABLE_CONTRACT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_contract_status_invalid")
    customer_company = _get_company(db, company_id=contract.customer_company_id, company_type=CompanyType.CUSTOMER)
    if payload.customer_company_id is not None:
        customer_company = _get_company(db, company_id=payload.customer_company_id, company_type=CompanyType.CUSTOMER)
        contract.customer_company_id = customer_company.id
    template = None
    version = None
    if payload.template_id is not None:
        template, version = _get_template(db, template_id=payload.template_id, template_type=TemplateType.SALES_CONTRACT)
        contract.template_id = template.id
        contract.template_version_id = version.id
    if payload.contract_date is not None:
        contract.contract_date = payload.contract_date
    if payload.deposit_rate is not None:
        contract.deposit_rate = _normalize_decimal(payload.deposit_rate, "0.0000")
    if template is None:
        template, version = _get_template(db, template_id=contract.template_id, template_type=TemplateType.SALES_CONTRACT)
    contract.template_snapshot_json = _build_contract_template_snapshot(template=template, version=version)
    _our_company_id, our_company_name = _resolve_operator_company_snapshot(db, current_user=current_user)
    if payload.items is not None:
        _rebuild_sales_contract_items(db, contract=contract, items=payload.items)
        prepared_items, item_metrics = _prepare_contract_items(db, items=payload.items)
    else:
        prepared_items, item_metrics = _prepare_existing_sales_contract_items(db, contract=contract)
    contract.variable_snapshot_json = _build_contract_variable_snapshot(
        contract_no=contract.contract_no,
        contract_date=contract.contract_date,
        deposit_rate=contract.deposit_rate,
        our_company_name=our_company_name,
        company_name=customer_company.company_name,
        warehouse_name=None,
        prepared_items=prepared_items,
        item_metrics=item_metrics,
        company_role="customer",
    )
    contract.updated_by = current_user.id
    return contract


def update_purchase_contract(db: Session, *, contract: PurchaseContract, payload: PurchaseContractUpdateRequest, current_user: User) -> PurchaseContract:
    if contract.status not in _EDITABLE_CONTRACT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_status_invalid")
    supplier_company = _get_company(db, company_id=contract.supplier_company_id, company_type=CompanyType.SUPPLIER)
    warehouse = _resolve_purchase_contract_snapshot_warehouse(db, snapshot=contract.template_snapshot_json)
    if payload.supplier_company_id is not None:
        supplier_company = _get_company(db, company_id=payload.supplier_company_id, company_type=CompanyType.SUPPLIER)
        contract.supplier_company_id = supplier_company.id
    template = None
    version = None
    if payload.template_id is not None:
        template, version = _get_template(db, template_id=payload.template_id, template_type=TemplateType.PURCHASE_CONTRACT)
        contract.template_id = template.id
        contract.template_version_id = version.id
    if payload.warehouse_id is not None:
        warehouse = _get_warehouse(db, warehouse_id=payload.warehouse_id)
    if payload.contract_date is not None:
        contract.contract_date = payload.contract_date
    if payload.deposit_rate is not None:
        contract.deposit_rate = _normalize_decimal(payload.deposit_rate, "0.0000")
    if template is None:
        template, version = _get_template(db, template_id=contract.template_id, template_type=TemplateType.PURCHASE_CONTRACT)
    contract.template_snapshot_json = _build_contract_template_snapshot(template=template, version=version, warehouse=warehouse)
    _our_company_id, our_company_name = _resolve_operator_company_snapshot(db, current_user=current_user)
    if payload.items is not None:
        _rebuild_purchase_contract_items(db, contract=contract, items=payload.items)
        prepared_items, item_metrics = _prepare_contract_items(db, items=payload.items)
    else:
        prepared_items, item_metrics = _prepare_existing_purchase_contract_items(db, contract=contract)
    contract.variable_snapshot_json = _build_contract_variable_snapshot(
        contract_no=contract.contract_no,
        contract_date=contract.contract_date,
        deposit_rate=contract.deposit_rate,
        our_company_name=our_company_name,
        company_name=supplier_company.company_name,
        warehouse_name=warehouse.name if warehouse is not None else "",
        prepared_items=prepared_items,
        item_metrics=item_metrics,
        company_role="supplier",
    )
    contract.updated_by = current_user.id
    return contract


def submit_effective_sales_contract(
    db: Session,
    *,
    contract: SalesContract,
    signed_contract_file_key: str,
    deposit_receipt_file_key: str,
    current_user: User,
) -> SalesContract:
    if contract.status not in _EDITABLE_CONTRACT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_contract_status_invalid")
    signed_asset = ensure_file_asset(db, file_key=signed_contract_file_key, business_type="sales_contract_signed", current_user=current_user)
    deposit_asset = ensure_file_asset(db, file_key=deposit_receipt_file_key, business_type="sales_contract_deposit", current_user=current_user)
    contract.signed_contract_file_id = signed_asset.id
    contract.deposit_receipt_file_id = deposit_asset.id
    contract.status = ContractStatus.EFFECTIVE
    contract.effective_at = datetime.now(UTC)
    contract.effective_by = current_user.id
    contract.updated_by = current_user.id
    return contract


def generate_sales_contract_pdf_file(
    db: Session,
    *,
    contract: SalesContract,
    current_user: User,
) -> str:
    file_key = generate_sales_contract_pdf(db=db, contract=contract)
    asset = ensure_file_asset(
        db,
        file_key=file_key,
        business_type="sales_contract_pdf",
        current_user=current_user,
        file_name=f"{contract.contract_no}.pdf",
    )
    replace_file_asset_links(
        db,
        entity_type="SALES_CONTRACT",
        entity_id=contract.id,
        field_name="generated_pdf",
        file_asset_ids=[asset.id],
    )
    return file_key


def submit_effective_purchase_contract(
    db: Session,
    *,
    contract: PurchaseContract,
    signed_contract_file_key: str,
    deposit_receipt_file_key: str,
    current_user: User,
) -> tuple[PurchaseContract, list[PurchaseStockIn]]:
    if contract.status not in _EDITABLE_CONTRACT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_status_invalid")
    signed_asset = ensure_file_asset(db, file_key=signed_contract_file_key, business_type="purchase_contract_signed", current_user=current_user)
    deposit_asset = ensure_file_asset(db, file_key=deposit_receipt_file_key, business_type="purchase_contract_deposit", current_user=current_user)
    contract.signed_contract_file_id = signed_asset.id
    contract.deposit_receipt_file_id = deposit_asset.id
    contract.status = ContractStatus.EFFECTIVE
    contract.effective_at = datetime.now(UTC)
    contract.effective_by = current_user.id
    contract.updated_by = current_user.id
    contract.pending_stock_in_qty = contract.effective_contract_qty

    warehouse = _resolve_purchase_contract_snapshot_warehouse(db, snapshot=contract.template_snapshot_json)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_warehouse_not_bound")
    warehouse_id = warehouse.id

    item_rows = db.scalars(
        select(PurchaseContractItem).where(PurchaseContractItem.purchase_contract_id == contract.id).order_by(PurchaseContractItem.id.asc())
    ).all()
    created_rows: list[PurchaseStockIn] = []
    for item in item_rows:
        stock_in = PurchaseStockIn(
            stock_in_no=build_purchase_stock_in_no(db, stock_in_date=contract.contract_date),
            purchase_contract_id=contract.id,
            warehouse_id=warehouse_id,
            product_id=item.product_id,
            stock_in_qty_ton=item.qty_ton,
            status=PurchaseStockInStatus.PENDING_CONFIRM,
            source_kind=PurchaseStockInSourceKind.PRIMARY_AUTO,
        )
        db.add(stock_in)
        db.flush()
        created_rows.append(stock_in)
    return contract, created_rows


def generate_purchase_contract_pdf_file(
    db: Session,
    *,
    contract: PurchaseContract,
    current_user: User,
) -> str:
    file_key = generate_purchase_contract_pdf(db=db, contract=contract)
    asset = ensure_file_asset(
        db,
        file_key=file_key,
        business_type="purchase_contract_pdf",
        current_user=current_user,
        file_name=f"{contract.contract_no}.pdf",
    )
    replace_file_asset_links(
        db,
        entity_type="PURCHASE_CONTRACT",
        entity_id=contract.id,
        field_name="generated_pdf",
        file_asset_ids=[asset.id],
    )
    return file_key


def _assert_sales_contract_voidable(db: Session, *, contract: SalesContract) -> None:
    if contract.status not in _VOIDABLE_CONTRACT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_contract_status_invalid")
    linked_order = db.scalar(select(SalesOrderV5.id).where(SalesOrderV5.sales_contract_id == contract.id))
    if linked_order is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sales_contract_has_business_refs")


def _assert_purchase_contract_voidable(db: Session, *, contract: PurchaseContract) -> None:
    if contract.status not in _VOIDABLE_CONTRACT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_status_invalid")
    linked_order = db.scalar(select(PurchaseOrderV5.id).where(PurchaseOrderV5.purchase_contract_id == contract.id))
    linked_stock_in = db.scalar(select(PurchaseStockIn.id).where(PurchaseStockIn.purchase_contract_id == contract.id))
    if linked_order is not None or linked_stock_in is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="purchase_contract_has_business_refs")


def void_sales_contract(db: Session, *, contract: SalesContract, reason: str, current_user: User) -> SalesContract:
    del reason
    _assert_sales_contract_voidable(db, contract=contract)
    contract.status = ContractStatus.VOIDED
    contract.voided_at = datetime.now(UTC)
    contract.voided_by = current_user.id
    contract.updated_by = current_user.id
    return contract


def void_purchase_contract(db: Session, *, contract: PurchaseContract, reason: str, current_user: User) -> PurchaseContract:
    del reason
    _assert_purchase_contract_voidable(db, contract=contract)
    contract.status = ContractStatus.VOIDED
    contract.voided_at = datetime.now(UTC)
    contract.voided_by = current_user.id
    contract.updated_by = current_user.id
    return contract


def _resolve_file_key(file_id: int | None, db: Session) -> str | None:
    from app.models.v5_domain import FileAsset

    if file_id is None:
        return None
    return db.scalar(select(FileAsset.file_key).where(FileAsset.id == file_id))


def _serialize_contract_items(items, product_name_map: dict[int, str]) -> list[ContractItemOut]:
    return [
        ContractItemOut(
            product_id=item.product_id,
            product_name=product_name_map.get(item.product_id, ""),
            qty_ton=float(item.qty_ton),
            unit_name=item.unit_name,
            tax_rate=float(item.tax_rate),
            unit_price_tax_included=float(item.unit_price_tax_included),
            amount_tax_included=float(item.amount_tax_included),
            amount_tax_excluded=float(item.amount_tax_excluded),
            tax_amount=float(item.tax_amount),
        )
        for item in items
    ]


def _build_sales_contract_item_map(db: Session, *, contract_ids: set[int]) -> dict[int, list[ContractItemOut]]:
    if not contract_ids:
        return {}
    items = db.scalars(
        select(SalesContractItem)
        .where(SalesContractItem.sales_contract_id.in_(contract_ids))
        .order_by(SalesContractItem.sales_contract_id.asc(), SalesContractItem.id.asc())
    ).all()
    product_ids = {item.product_id for item in items}
    product_name_map = (
        dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(product_ids))).all())
        if product_ids
        else {}
    )
    result: dict[int, list[ContractItemOut]] = {}
    for item in items:
        result.setdefault(item.sales_contract_id, []).append(
            ContractItemOut(
                product_id=item.product_id,
                product_name=product_name_map.get(item.product_id, ""),
                qty_ton=float(item.qty_ton),
                unit_name=item.unit_name,
                tax_rate=float(item.tax_rate),
                unit_price_tax_included=float(item.unit_price_tax_included),
                amount_tax_included=float(item.amount_tax_included),
                amount_tax_excluded=float(item.amount_tax_excluded),
                tax_amount=float(item.tax_amount),
            )
        )
    return result


def _build_purchase_contract_item_map(db: Session, *, contract_ids: set[int]) -> dict[int, list[ContractItemOut]]:
    if not contract_ids:
        return {}
    items = db.scalars(
        select(PurchaseContractItem)
        .where(PurchaseContractItem.purchase_contract_id.in_(contract_ids))
        .order_by(PurchaseContractItem.purchase_contract_id.asc(), PurchaseContractItem.id.asc())
    ).all()
    product_ids = {item.product_id for item in items}
    product_name_map = (
        dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(product_ids))).all())
        if product_ids
        else {}
    )
    result: dict[int, list[ContractItemOut]] = {}
    for item in items:
        result.setdefault(item.purchase_contract_id, []).append(
            ContractItemOut(
                product_id=item.product_id,
                product_name=product_name_map.get(item.product_id, ""),
                qty_ton=float(item.qty_ton),
                unit_name=item.unit_name,
                tax_rate=float(item.tax_rate),
                unit_price_tax_included=float(item.unit_price_tax_included),
                amount_tax_included=float(item.amount_tax_included),
                amount_tax_excluded=float(item.amount_tax_excluded),
                tax_amount=float(item.tax_amount),
            )
        )
    return result


def _build_contract_product_name_map(
    db: Session,
    *,
    sales_rows: list[SalesContract] | None = None,
    purchase_rows: list[PurchaseContract] | None = None,
) -> dict[int, str]:
    product_name_map: dict[int, str] = {}
    sales_rows = sales_rows or []
    purchase_rows = purchase_rows or []

    missing_sales_ids = [
        item.id
        for item in sales_rows
        if not str((item.variable_snapshot_json or {}).get("product_name") or "").strip()
    ]
    if missing_sales_ids:
        sales_items = db.scalars(
            select(SalesContractItem).where(SalesContractItem.sales_contract_id.in_(missing_sales_ids)).order_by(SalesContractItem.id.asc())
        ).all()
        oil_product_ids = {item.product_id for item in sales_items}
        oil_product_name_map = (
            dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(oil_product_ids))).all())
            if oil_product_ids
            else {}
        )
        aggregated_sales_names: dict[int, list[str]] = {}
        for item in sales_items:
            product_name = str(oil_product_name_map.get(item.product_id) or "").strip()
            if not product_name:
                continue
            contract_names = aggregated_sales_names.setdefault(item.sales_contract_id, [])
            if product_name not in contract_names:
                contract_names.append(product_name)
        for contract_id, names in aggregated_sales_names.items():
            product_name_map[contract_id] = "、".join(names)

    missing_purchase_ids = [
        item.id
        for item in purchase_rows
        if not str((item.variable_snapshot_json or {}).get("product_name") or "").strip()
    ]
    if missing_purchase_ids:
        purchase_items = db.scalars(
            select(PurchaseContractItem)
            .where(PurchaseContractItem.purchase_contract_id.in_(missing_purchase_ids))
            .order_by(PurchaseContractItem.id.asc())
        ).all()
        oil_product_ids = {item.product_id for item in purchase_items}
        oil_product_name_map = (
            dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_(oil_product_ids))).all())
            if oil_product_ids
            else {}
        )
        aggregated_purchase_names: dict[int, list[str]] = {}
        for item in purchase_items:
            product_name = str(oil_product_name_map.get(item.product_id) or "").strip()
            if not product_name:
                continue
            contract_names = aggregated_purchase_names.setdefault(item.purchase_contract_id, [])
            if product_name not in contract_names:
                contract_names.append(product_name)
        for contract_id, names in aggregated_purchase_names.items():
            product_name_map[contract_id] = "、".join(names)

    return product_name_map


def serialize_sales_contract_list(db: Session, *, rows: list[SalesContract]) -> list[SalesContractListItemOut]:
    if not rows:
        return []
    customer_company_ids = {item.customer_company_id for item in rows}
    template_ids = {item.template_id for item in rows}
    contract_ids = {item.id for item in rows}
    customer_name_map = dict(db.execute(select(Company.id, Company.company_name).where(Company.id.in_(customer_company_ids))).all())
    template_name_map = dict(db.execute(select(AgreementTemplate.id, AgreementTemplate.template_name).where(AgreementTemplate.id.in_(template_ids))).all())
    product_name_map = _build_contract_product_name_map(db, sales_rows=rows)
    contract_item_map = _build_sales_contract_item_map(db, contract_ids=contract_ids)
    result: list[SalesContractListItemOut] = []
    for item in rows:
        contract_items = contract_item_map.get(item.id, [])
        signed_contract_file_key = _resolve_file_key(item.signed_contract_file_id, db)
        deposit_receipt_file_key = _resolve_file_key(item.deposit_receipt_file_id, db)
        generated_pdf_file_key = None
        generated_pdf_keys = list_file_keys_by_link(db, entity_type="SALES_CONTRACT", entity_id=item.id, field_name="generated_pdf")
        if generated_pdf_keys:
            generated_pdf_file_key = generated_pdf_keys[0]
        result.append(
            SalesContractListItemOut(
                id=item.id,
                contract_no=item.contract_no,
                customer_company_id=item.customer_company_id,
                customer_company_name=customer_name_map.get(item.customer_company_id, ""),
                product_name=str((item.variable_snapshot_json or {}).get("product_name") or "").strip() or product_name_map.get(item.id, ""),
                template_id=item.template_id,
                template_name=template_name_map.get(item.template_id, ""),
                contract_date=item.contract_date,
                status=item.status,
                item_count=len(contract_items),
                contract_items=contract_items,
                deposit_rate=float(item.deposit_rate),
                deposit_amount=float(item.deposit_amount),
                base_contract_qty=float(item.base_contract_qty),
                effective_contract_qty=float(item.effective_contract_qty),
                executed_qty=float(item.executed_qty),
                pending_execution_qty=float(item.pending_execution_qty),
                over_executed_qty=float(item.over_executed_qty),
                signed_contract_file_key=signed_contract_file_key,
                signed_contract_file_url=build_protected_file_url_by_key(signed_contract_file_key) if signed_contract_file_key else None,
                deposit_receipt_file_key=deposit_receipt_file_key,
                deposit_receipt_file_url=build_protected_file_url_by_key(deposit_receipt_file_key) if deposit_receipt_file_key else None,
                generated_pdf_file_key=generated_pdf_file_key,
                generated_pdf_file_url=build_protected_file_url_by_key(generated_pdf_file_key) if generated_pdf_file_key else None,
                effective_at=item.effective_at,
                effective_by=item.effective_by,
                voided_at=item.voided_at,
                voided_by=item.voided_by,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return result


def serialize_sales_contract_detail(db: Session, *, row: SalesContract) -> SalesContractDetailOut:
    list_item = serialize_sales_contract_list(db, rows=[row])[0]
    items = db.scalars(select(SalesContractItem).where(SalesContractItem.sales_contract_id == row.id).order_by(SalesContractItem.id.asc())).all()
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_({item.product_id for item in items}))).all()) if items else {}
    return SalesContractDetailOut(
        **list_item.model_dump(),
        variable_snapshot=row.variable_snapshot_json,
        template_snapshot=row.template_snapshot_json,
        items=_serialize_contract_items(items, product_name_map),
    )


def serialize_purchase_contract_list(db: Session, *, rows: list[PurchaseContract]) -> list[PurchaseContractListItemOut]:
    if not rows:
        return []
    supplier_company_ids = {item.supplier_company_id for item in rows}
    template_ids = {item.template_id for item in rows}
    contract_ids = {item.id for item in rows}
    supplier_name_map = dict(db.execute(select(Company.id, Company.company_name).where(Company.id.in_(supplier_company_ids))).all())
    template_name_map = dict(db.execute(select(AgreementTemplate.id, AgreementTemplate.template_name).where(AgreementTemplate.id.in_(template_ids))).all())
    product_name_map = _build_contract_product_name_map(db, purchase_rows=rows)
    contract_item_map = _build_purchase_contract_item_map(db, contract_ids=contract_ids)
    result: list[PurchaseContractListItemOut] = []
    for item in rows:
        contract_items = contract_item_map.get(item.id, [])
        warehouse = _resolve_purchase_contract_snapshot_warehouse(db, snapshot=item.template_snapshot_json)
        warehouse_id = warehouse.id if warehouse is not None else _parse_snapshot_warehouse_id(item.template_snapshot_json)
        warehouse_name = warehouse.name if warehouse is not None else str((item.template_snapshot_json or {}).get("warehouse_name") or "").strip()
        signed_contract_file_key = _resolve_file_key(item.signed_contract_file_id, db)
        deposit_receipt_file_key = _resolve_file_key(item.deposit_receipt_file_id, db)
        generated_pdf_file_key = None
        generated_pdf_keys = list_file_keys_by_link(db, entity_type="PURCHASE_CONTRACT", entity_id=item.id, field_name="generated_pdf")
        if generated_pdf_keys:
            generated_pdf_file_key = generated_pdf_keys[0]
        result.append(
            PurchaseContractListItemOut(
                id=item.id,
                contract_no=item.contract_no,
                supplier_company_id=item.supplier_company_id,
                supplier_company_name=supplier_name_map.get(item.supplier_company_id, ""),
                product_name=str((item.variable_snapshot_json or {}).get("product_name") or "").strip() or product_name_map.get(item.id, ""),
                warehouse_id=warehouse_id,
                warehouse_name=warehouse_name,
                template_id=item.template_id,
                template_name=template_name_map.get(item.template_id, ""),
                contract_date=item.contract_date,
                status=item.status,
                item_count=len(contract_items),
                contract_items=contract_items,
                deposit_rate=float(item.deposit_rate),
                deposit_amount=float(item.deposit_amount),
                base_contract_qty=float(item.base_contract_qty),
                effective_contract_qty=float(item.effective_contract_qty),
                executed_qty=float(item.executed_qty),
                pending_execution_qty=float(item.pending_execution_qty),
                over_executed_qty=float(item.over_executed_qty),
                stocked_in_qty=float(item.stocked_in_qty),
                pending_stock_in_qty=float(item.pending_stock_in_qty),
                signed_contract_file_key=signed_contract_file_key,
                signed_contract_file_url=build_protected_file_url_by_key(signed_contract_file_key) if signed_contract_file_key else None,
                deposit_receipt_file_key=deposit_receipt_file_key,
                deposit_receipt_file_url=build_protected_file_url_by_key(deposit_receipt_file_key) if deposit_receipt_file_key else None,
                generated_pdf_file_key=generated_pdf_file_key,
                generated_pdf_file_url=build_protected_file_url_by_key(generated_pdf_file_key) if generated_pdf_file_key else None,
                effective_at=item.effective_at,
                effective_by=item.effective_by,
                voided_at=item.voided_at,
                voided_by=item.voided_by,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return result


def serialize_purchase_contract_detail(db: Session, *, row: PurchaseContract) -> PurchaseContractDetailOut:
    list_item = serialize_purchase_contract_list(db, rows=[row])[0]
    items = db.scalars(select(PurchaseContractItem).where(PurchaseContractItem.purchase_contract_id == row.id).order_by(PurchaseContractItem.id.asc())).all()
    product_name_map = dict(db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_({item.product_id for item in items}))).all()) if items else {}
    return PurchaseContractDetailOut(
        **list_item.model_dump(),
        variable_snapshot=row.variable_snapshot_json,
        template_snapshot=row.template_snapshot_json,
        items=_serialize_contract_items(items, product_name_map),
    )
