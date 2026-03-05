from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.v5_dashboard import OverviewSummaryOut
from app.services.business_log_service import write_business_log
from app.services.v5_dashboard_service import build_overview_summary

router = APIRouter(tags=["v5-dashboard"])


@router.get("/dashboard/overview", response_model=OverviewSummaryOut)
def get_v5_dashboard_overview(
    request: Request,
    low_stock_threshold: float = Query(default=10.0, ge=0),
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> OverviewSummaryOut:
    result = build_overview_summary(
        db=db,
        current_user=current_user,
        low_stock_threshold=low_stock_threshold,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_DASHBOARD_OVERVIEW",
        result="SUCCESS",
        user=current_user,
        entity_type="DASHBOARD",
        detail_json=result.model_dump(),
        auto_commit=True,
    )
    return result
