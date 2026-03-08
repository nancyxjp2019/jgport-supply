from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, require_actor
from app.db.session import get_db
from app.schemas.company import (
    CompanyCreateRequest,
    CompanyDetailResponse,
    CompanyListResponse,
    CompanyStatusUpdateRequest,
    CompanyUpdateRequest,
)
from app.services.company_service import (
    change_company_profile_status,
    create_company_profile,
    get_company_profile,
    list_company_profiles,
    update_company_profile,
)

router = APIRouter(prefix="/companies", tags=["companies"])
admin_actor_dependency = require_actor(
    allowed_roles={"admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)


@router.get("", response_model=CompanyListResponse)
def get_companies(
    company_type: str | None = Query(default=None, max_length=32),
    status_text: str | None = Query(default=None, alias="status", max_length=16),
    _: AuthenticatedActor = Depends(admin_actor_dependency),
    db: Session = Depends(get_db),
) -> CompanyListResponse:
    items, total = list_company_profiles(
        db, company_type=company_type, status_text=status_text
    )
    return CompanyListResponse(items=items, total=total, message="查询成功")


@router.get("/{company_id}", response_model=CompanyDetailResponse)
def get_company_detail(
    company_id: str,
    _: AuthenticatedActor = Depends(admin_actor_dependency),
    db: Session = Depends(get_db),
) -> CompanyDetailResponse:
    return CompanyDetailResponse(**get_company_profile(db, company_id))


@router.post("", response_model=CompanyDetailResponse, status_code=201)
def create_company(
    payload: CompanyCreateRequest,
    actor: AuthenticatedActor = Depends(admin_actor_dependency),
    db: Session = Depends(get_db),
) -> CompanyDetailResponse:
    result = create_company_profile(
        db,
        company_id=payload.company_id,
        company_name=payload.company_name,
        company_type=payload.company_type,
        parent_company_id=payload.parent_company_id,
        remark=payload.remark,
        actor=actor,
    )
    return CompanyDetailResponse(**result)


@router.put("/{company_id}", response_model=CompanyDetailResponse)
def update_company(
    company_id: str,
    payload: CompanyUpdateRequest,
    actor: AuthenticatedActor = Depends(admin_actor_dependency),
    db: Session = Depends(get_db),
) -> CompanyDetailResponse:
    result = update_company_profile(
        db,
        company_id=company_id,
        company_name=payload.company_name,
        parent_company_id=payload.parent_company_id,
        remark=payload.remark,
        actor=actor,
    )
    return CompanyDetailResponse(**result)


@router.post("/{company_id}/status", response_model=CompanyDetailResponse)
def update_company_status(
    company_id: str,
    payload: CompanyStatusUpdateRequest,
    actor: AuthenticatedActor = Depends(admin_actor_dependency),
    db: Session = Depends(get_db),
) -> CompanyDetailResponse:
    result = change_company_profile_status(
        db,
        company_id=company_id,
        enabled=payload.enabled,
        reason=payload.reason,
        actor=actor,
    )
    return CompanyDetailResponse(**result)
