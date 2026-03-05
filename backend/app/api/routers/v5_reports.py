from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import BRIDGE_ADMIN_USERNAME
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.v5_domain import ReportType
from app.schemas.v5_report import ReportExportItemOut, ReportExportListOut, ReportGenerateRequest
from app.services.business_log_service import write_business_log
from app.services.v5_report_service import (
    ReportGenerateTooFrequentError,
    generate_report_export,
    list_report_exports,
    serialize_report_export_list,
)

router = APIRouter(tags=["v5-reports"])


@router.post("/reports/sales-orders/generate", response_model=ReportExportItemOut)
def generate_sales_order_report(
    payload: ReportGenerateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportItemOut:
    return _generate_report(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.SALES_ORDERS,
        payload=payload,
    )


@router.get("/reports/sales-orders", response_model=ReportExportListOut)
def list_sales_order_reports(
    request: Request,
    days: int | None = Query(default=30, ge=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportListOut:
    return _list_reports(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.SALES_ORDERS,
        days=days,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.post("/reports/purchase-orders/generate", response_model=ReportExportItemOut)
def generate_purchase_order_report(
    payload: ReportGenerateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.SUPPLIER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportItemOut:
    return _generate_report(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.PURCHASE_ORDERS,
        payload=payload,
    )


@router.get("/reports/purchase-orders", response_model=ReportExportListOut)
def list_purchase_order_reports(
    request: Request,
    days: int | None = Query(default=30, ge=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles(UserRole.SUPPLIER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportListOut:
    return _list_reports(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.PURCHASE_ORDERS,
        days=days,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.post("/reports/sales-contracts/generate", response_model=ReportExportItemOut)
def generate_sales_contract_report(
    payload: ReportGenerateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportItemOut:
    return _generate_report(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.SALES_CONTRACTS,
        payload=payload,
    )


@router.get("/reports/sales-contracts", response_model=ReportExportListOut)
def list_sales_contract_reports(
    request: Request,
    days: int | None = Query(default=30, ge=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportListOut:
    return _list_reports(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.SALES_CONTRACTS,
        days=days,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.post("/reports/purchase-contracts/generate", response_model=ReportExportItemOut)
def generate_purchase_contract_report(
    payload: ReportGenerateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.SUPPLIER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportItemOut:
    return _generate_report(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.PURCHASE_CONTRACTS,
        payload=payload,
    )


@router.get("/reports/purchase-contracts", response_model=ReportExportListOut)
def list_purchase_contract_reports(
    request: Request,
    days: int | None = Query(default=30, ge=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles(UserRole.SUPPLIER, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportListOut:
    return _list_reports(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.PURCHASE_CONTRACTS,
        days=days,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.post("/reports/inventory-movements/generate", response_model=ReportExportItemOut)
def generate_inventory_movement_report(
    payload: ReportGenerateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportItemOut:
    return _generate_report(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.INVENTORY_MOVEMENTS,
        payload=payload,
    )


@router.get("/reports/inventory-movements", response_model=ReportExportListOut)
def list_inventory_movement_reports(
    request: Request,
    days: int | None = Query(default=30, ge=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles(UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportListOut:
    return _list_reports(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.INVENTORY_MOVEMENTS,
        days=days,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.post("/reports/warehouse-ledger/generate", response_model=ReportExportItemOut)
def generate_warehouse_ledger_report(
    payload: ReportGenerateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.WAREHOUSE, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportItemOut:
    return _generate_report(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.WAREHOUSE_LEDGER,
        payload=payload,
    )


@router.get("/reports/warehouse-ledger", response_model=ReportExportListOut)
def list_warehouse_ledger_reports(
    request: Request,
    days: int | None = Query(default=30, ge=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles(UserRole.WAREHOUSE, UserRole.OPERATOR, UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ReportExportListOut:
    return _list_reports(
        db=db,
        request=request,
        current_user=current_user,
        report_type=ReportType.WAREHOUSE_LEDGER,
        days=days,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


def _generate_report(
    *,
    db: Session,
    request: Request,
    current_user: User,
    report_type: ReportType,
    payload: ReportGenerateRequest,
) -> ReportExportItemOut:
    try:
        row = generate_report_export(
            db=db,
            report_type=report_type,
            current_user=current_user,
            days=payload.days,
            from_date=payload.from_date,
            to_date=payload.to_date,
        )
    except ReportGenerateTooFrequentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    write_business_log(
        db=db,
        request=request,
        action=f"V5_{report_type.value}_REPORT_GENERATE",
        result="SUCCESS",
        user=current_user,
        entity_type="REPORT_EXPORT",
        entity_id=str(row.id),
        detail_json={"report_type": report_type.value, "row_count": row.row_count},
    )
    db.commit()
    db.refresh(row)
    return serialize_report_export_list(db=db, rows=[row])[0]


def _list_reports(
    *,
    db: Session,
    request: Request,
    current_user: User,
    report_type: ReportType,
    days: int | None,
    from_date: date | None,
    to_date: date | None,
    limit: int,
    offset: int,
) -> ReportExportListOut:
    effective_limit = limit if current_user.username == BRIDGE_ADMIN_USERNAME else min(limit, 5)
    rows, total = list_report_exports(
        db=db,
        report_type=report_type,
        current_user=current_user,
        days=days,
        from_date=from_date,
        to_date=to_date,
        limit=effective_limit,
        offset=offset,
    )
    items = serialize_report_export_list(db=db, rows=rows)
    write_business_log(
        db=db,
        request=request,
        action=f"V5_{report_type.value}_REPORT_LIST",
        result="SUCCESS",
        user=current_user,
        entity_type="REPORT_EXPORT",
        detail_json={"report_type": report_type.value, "count": len(items)},
        auto_commit=True,
    )
    return ReportExportListOut(items=items, total=total, limit=effective_limit, offset=offset)
