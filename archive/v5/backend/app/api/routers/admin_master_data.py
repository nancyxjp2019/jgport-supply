from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AdminOperator, get_admin_operator
from app.db.session import get_db
from app.models.master_data import OilProduct, Warehouse
from app.models.user import User
from app.models.v5_domain import (
    Company,
    CompanyType,
    CustomerTransportProfile,
    PurchaseContract,
    PurchaseOrderV5,
    PurchaseStockIn,
    SalesContract,
    SalesOrderV5,
    InventoryAdjustment,
    InventoryMovement,
)
from app.schemas.master_data import (
    CompanyCreateRequest,
    CompanyOut,
    CompanyUpdateRequest,
    OilProductCreateRequest,
    OilProductOut,
    OilProductUpdateRequest,
    WarehouseCreateRequest,
    WarehouseOut,
    WarehouseUpdateRequest,
)
from app.services.business_log_service import write_business_log

router = APIRouter(prefix="/admin", tags=["admin-master-data"])


def _normalize_name(raw_name: str, field_label: str) -> str:
    name = raw_name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field_label}_empty")
    return name


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    return value or None


def _resolve_company_or_404(db: Session, *, company_id: int, detail: str = "company_not_found") -> Company:
    row = db.scalar(select(Company).where(Company.id == company_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return row


def _has_result(db: Session, statement) -> bool:
    return db.scalar(statement.limit(1)) is not None


def _ensure_active_warehouse_company(company: Company) -> None:
    if not company.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="warehouse_company_not_active")
    if company.company_type != CompanyType.WAREHOUSE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="warehouse_company_type_invalid")


def _company_type_locked(db: Session, *, company_id: int) -> bool:
    return any(
        (
            _has_result(db, select(User.id).where(User.company_id == company_id)),
            _has_result(db, select(SalesContract.id).where(SalesContract.customer_company_id == company_id)),
            _has_result(db, select(PurchaseContract.id).where(PurchaseContract.supplier_company_id == company_id)),
            _has_result(db, select(SalesOrderV5.id).where(SalesOrderV5.customer_company_id == company_id)),
            _has_result(db, select(SalesOrderV5.id).where(SalesOrderV5.operator_company_id == company_id)),
            _has_result(db, select(PurchaseOrderV5.id).where(PurchaseOrderV5.supplier_company_id == company_id)),
            _has_result(db, select(CustomerTransportProfile.id).where(CustomerTransportProfile.customer_company_id == company_id)),
            _has_result(db, select(Warehouse.id).where(Warehouse.company_id == company_id)),
        )
    )


def _warehouse_company_binding_locked(db: Session, *, warehouse_id: int) -> bool:
    return any(
        (
            _has_result(db, select(PurchaseOrderV5.id).where(PurchaseOrderV5.warehouse_id == warehouse_id)),
            _has_result(db, select(PurchaseStockIn.id).where(PurchaseStockIn.warehouse_id == warehouse_id)),
            _has_result(db, select(InventoryMovement.id).where(InventoryMovement.warehouse_id == warehouse_id)),
            _has_result(db, select(InventoryAdjustment.id).where(InventoryAdjustment.warehouse_id == warehouse_id)),
        )
    )


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    request: Request,
    active_only: bool = Query(default=False),
    company_type: CompanyType | None = Query(default=None),
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> list[CompanyOut]:
    query = select(Company)
    if active_only:
        query = query.where(Company.is_active.is_(True))
    if company_type is not None:
        query = query.where(Company.company_type == company_type)
    rows = db.scalars(query.order_by(Company.company_type.asc(), Company.company_name.asc(), Company.id.asc())).all()
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_COMPANY_LIST",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="COMPANY",
        detail_json={
            "count": len(rows),
            "active_only": active_only,
            "company_type": company_type.value if company_type else None,
        },
        auto_commit=True,
    )
    return [CompanyOut.model_validate(item) for item in rows]


@router.post("/companies", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> CompanyOut:
    company_code = _normalize_name(payload.company_code, "company_code")
    company_name = _normalize_name(payload.company_name, "company_name")
    if db.scalar(select(Company.id).where(Company.company_code == company_code)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="company_code_exists")
    row = Company(
        company_code=company_code,
        company_name=company_name,
        company_type=payload.company_type,
        tax_no=_normalize_optional_text(payload.tax_no),
        contact_name=_normalize_optional_text(payload.contact_name),
        contact_phone=_normalize_optional_text(payload.contact_phone),
        address=_normalize_optional_text(payload.address),
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_COMPANY_CREATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="COMPANY",
        entity_id=str(row.id),
        detail_json={
            "company_code": row.company_code,
            "company_type": row.company_type.value,
        },
    )
    db.commit()
    db.refresh(row)
    return CompanyOut.model_validate(row)


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    payload: CompanyUpdateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> CompanyOut:
    row = _resolve_company_or_404(db=db, company_id=company_id)
    if "company_code" in payload.model_fields_set and payload.company_code is not None:
        next_code = _normalize_name(payload.company_code, "company_code")
        exists = db.scalar(select(Company.id).where(Company.company_code == next_code, Company.id != row.id))
        if exists is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="company_code_exists")
        row.company_code = next_code
    if "company_name" in payload.model_fields_set and payload.company_name is not None:
        row.company_name = _normalize_name(payload.company_name, "company_name")
    if "company_type" in payload.model_fields_set and payload.company_type is not None:
        if payload.company_type != row.company_type and _company_type_locked(db=db, company_id=row.id):
            write_business_log(
                db=db,
                request=request,
                action="ADMIN_COMPANY_UPDATE",
                result="FAILED",
                user=admin.user,
                actor_user_id=admin.actor_id,
                role=admin.role,
                entity_type="COMPANY",
                entity_id=str(row.id),
                reason="公司类型已被业务引用锁定",
                detail_json={
                    "before_company_type": row.company_type.value,
                    "after_company_type": payload.company_type.value,
                },
                auto_commit=True,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="company_type_locked")
        row.company_type = payload.company_type
    if "tax_no" in payload.model_fields_set:
        row.tax_no = _normalize_optional_text(payload.tax_no)
    if "contact_name" in payload.model_fields_set:
        row.contact_name = _normalize_optional_text(payload.contact_name)
    if "contact_phone" in payload.model_fields_set:
        row.contact_phone = _normalize_optional_text(payload.contact_phone)
    if "address" in payload.model_fields_set:
        row.address = _normalize_optional_text(payload.address)
    if payload.is_active is not None:
        row.is_active = payload.is_active

    write_business_log(
        db=db,
        request=request,
        action="ADMIN_COMPANY_UPDATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="COMPANY",
        entity_id=str(row.id),
        detail_json={
            "company_code": row.company_code,
            "company_name": row.company_name,
            "company_type": row.company_type.value,
            "is_active": row.is_active,
        },
    )
    db.commit()
    db.refresh(row)
    return CompanyOut.model_validate(row)


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(
    request: Request,
    active_only: bool = Query(default=False),
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> list[WarehouseOut]:
    query = select(Warehouse)
    if active_only:
        query = query.where(Warehouse.is_active.is_(True))
    rows = db.scalars(query.order_by(Warehouse.id.desc())).all()
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_WAREHOUSE_LIST",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="WAREHOUSE",
        detail_json={"count": len(rows), "active_only": active_only},
        auto_commit=True,
    )
    return [WarehouseOut.model_validate(item) for item in rows]


@router.post("/warehouses", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> WarehouseOut:
    name = _normalize_name(payload.name, "warehouse_name")
    warehouse_code = _normalize_optional_text(payload.warehouse_code)
    exists = db.scalar(select(Warehouse).where(Warehouse.name == name))
    if exists is not None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_WAREHOUSE_CREATE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="WAREHOUSE",
            reason="仓库名称已存在",
            detail_json={"name": name},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="warehouse_name_exists")
    if warehouse_code and db.scalar(select(Warehouse.id).where(Warehouse.warehouse_code == warehouse_code)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="warehouse_code_exists")
    company = None
    if payload.company_id is not None:
        company = _resolve_company_or_404(db=db, company_id=payload.company_id)
        _ensure_active_warehouse_company(company)

    row = Warehouse(
        name=name,
        warehouse_code=warehouse_code,
        company_id=company.id if company is not None else None,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_WAREHOUSE_CREATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="WAREHOUSE",
        entity_id=str(row.id),
        detail_json={"name": row.name, "warehouse_code": row.warehouse_code, "company_id": row.company_id},
    )
    db.commit()
    db.refresh(row)
    return WarehouseOut.model_validate(row)


@router.patch("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(
    warehouse_id: int,
    payload: WarehouseUpdateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> WarehouseOut:
    row = db.scalar(select(Warehouse).where(Warehouse.id == warehouse_id))
    if row is None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_WAREHOUSE_UPDATE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="WAREHOUSE",
            entity_id=str(warehouse_id),
            reason="仓库不存在",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="warehouse_not_found")

    if payload.name is not None:
        next_name = _normalize_name(payload.name, "warehouse_name")
        if next_name != row.name:
            exists = db.scalar(select(Warehouse).where(Warehouse.name == next_name, Warehouse.id != row.id))
            if exists is not None:
                write_business_log(
                    db=db,
                    request=request,
                    action="ADMIN_WAREHOUSE_UPDATE",
                    result="FAILED",
                    user=admin.user,
                    actor_user_id=admin.actor_id,
                    role=admin.role,
                    entity_type="WAREHOUSE",
                    entity_id=str(warehouse_id),
                    reason="仓库名称已存在",
                    detail_json={"name": next_name},
                    auto_commit=True,
                )
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="warehouse_name_exists")
            row.name = next_name
    if "warehouse_code" in payload.model_fields_set:
        next_code = _normalize_optional_text(payload.warehouse_code)
        if next_code != row.warehouse_code:
            if next_code and db.scalar(select(Warehouse.id).where(Warehouse.warehouse_code == next_code, Warehouse.id != row.id)) is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="warehouse_code_exists")
            row.warehouse_code = next_code
    if "company_id" in payload.model_fields_set:
        next_company_id = payload.company_id
        if next_company_id != row.company_id and _warehouse_company_binding_locked(db=db, warehouse_id=row.id):
            write_business_log(
                db=db,
                request=request,
                action="ADMIN_WAREHOUSE_UPDATE",
                result="FAILED",
                user=admin.user,
                actor_user_id=admin.actor_id,
                role=admin.role,
                entity_type="WAREHOUSE",
                entity_id=str(row.id),
                reason="仓库归属已被业务引用锁定",
                detail_json={
                    "before_company_id": row.company_id,
                    "after_company_id": next_company_id,
                },
                auto_commit=True,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="warehouse_company_locked")
        if next_company_id is None:
            row.company_id = None
        else:
            company = _resolve_company_or_404(db=db, company_id=next_company_id)
            _ensure_active_warehouse_company(company)
            row.company_id = company.id

    if payload.is_active is not None:
        row.is_active = payload.is_active

    write_business_log(
        db=db,
        request=request,
        action="ADMIN_WAREHOUSE_UPDATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="WAREHOUSE",
        entity_id=str(row.id),
        detail_json={
            "name": row.name,
            "warehouse_code": row.warehouse_code,
            "company_id": row.company_id,
            "is_active": row.is_active,
        },
    )
    db.commit()
    db.refresh(row)
    return WarehouseOut.model_validate(row)


@router.get("/products", response_model=list[OilProductOut])
def list_products(
    request: Request,
    active_only: bool = Query(default=False),
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> list[OilProductOut]:
    query = select(OilProduct)
    if active_only:
        query = query.where(OilProduct.is_active.is_(True))
    rows = db.scalars(query.order_by(OilProduct.id.desc())).all()
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_PRODUCT_LIST",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="PRODUCT",
        detail_json={"count": len(rows), "active_only": active_only},
        auto_commit=True,
    )
    return [OilProductOut.model_validate(item) for item in rows]


@router.post("/products", response_model=OilProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: OilProductCreateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> OilProductOut:
    name = _normalize_name(payload.name, "product_name")
    product_code = _normalize_optional_text(payload.product_code)
    unit_name = _normalize_name(payload.unit_name, "unit_name")
    exists = db.scalar(select(OilProduct).where(OilProduct.name == name))
    if exists is not None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_PRODUCT_CREATE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="PRODUCT",
            reason="油品名称已存在",
            detail_json={"name": name},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="product_name_exists")
    if product_code and db.scalar(select(OilProduct.id).where(OilProduct.product_code == product_code)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="product_code_exists")

    row = OilProduct(name=name, product_code=product_code, unit_name=unit_name, is_active=payload.is_active)
    db.add(row)
    db.flush()
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_PRODUCT_CREATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="PRODUCT",
        entity_id=str(row.id),
        detail_json={"name": row.name, "product_code": row.product_code, "unit_name": row.unit_name},
    )
    db.commit()
    db.refresh(row)
    return OilProductOut.model_validate(row)


@router.patch("/products/{product_id}", response_model=OilProductOut)
def update_product(
    product_id: int,
    payload: OilProductUpdateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> OilProductOut:
    row = db.scalar(select(OilProduct).where(OilProduct.id == product_id))
    if row is None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_PRODUCT_UPDATE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="PRODUCT",
            entity_id=str(product_id),
            reason="油品不存在",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product_not_found")

    if payload.name is not None:
        next_name = _normalize_name(payload.name, "product_name")
        if next_name != row.name:
            exists = db.scalar(select(OilProduct).where(OilProduct.name == next_name, OilProduct.id != row.id))
            if exists is not None:
                write_business_log(
                    db=db,
                    request=request,
                    action="ADMIN_PRODUCT_UPDATE",
                    result="FAILED",
                    user=admin.user,
                    actor_user_id=admin.actor_id,
                    role=admin.role,
                    entity_type="PRODUCT",
                    entity_id=str(product_id),
                    reason="油品名称已存在",
                    detail_json={"name": next_name},
                    auto_commit=True,
                )
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="product_name_exists")
            row.name = next_name
    if "product_code" in payload.model_fields_set:
        next_code = _normalize_optional_text(payload.product_code)
        if next_code != row.product_code:
            if next_code and db.scalar(select(OilProduct.id).where(OilProduct.product_code == next_code, OilProduct.id != row.id)) is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="product_code_exists")
            row.product_code = next_code
    if "unit_name" in payload.model_fields_set and payload.unit_name is not None:
        row.unit_name = _normalize_name(payload.unit_name, "unit_name")

    if payload.is_active is not None:
        row.is_active = payload.is_active

    write_business_log(
        db=db,
        request=request,
        action="ADMIN_PRODUCT_UPDATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="PRODUCT",
        entity_id=str(row.id),
        detail_json={
            "name": row.name,
            "product_code": row.product_code,
            "unit_name": row.unit_name,
            "is_active": row.is_active,
        },
    )
    db.commit()
    db.refresh(row)
    return OilProductOut.model_validate(row)
