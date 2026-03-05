from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AdminOperator, get_admin_operator
from app.db.session import get_db
from app.models.v5_domain import TemplateStatus, TemplateType
from app.schemas.v5_template import (
    AgreementTemplateCreateRequest,
    AgreementTemplateDetailOut,
    AgreementTemplateListItemOut,
    AgreementTemplateStatusUpdateRequest,
    AgreementTemplateUpdateRequest,
)
from app.services.business_log_service import write_business_log
from app.services.v5_template_service import (
    create_agreement_template,
    get_agreement_template_or_404,
    list_agreement_templates,
    serialize_agreement_template_detail,
    set_agreement_template_default,
    update_agreement_template,
    update_agreement_template_status,
)

router = APIRouter(prefix="/admin", tags=["admin-agreement-templates"])


def _require_super_admin(admin: AdminOperator) -> AdminOperator:
    if admin.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="super_admin_only")
    if admin.user is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="bridge_admin_user_missing")
    return admin


@router.get("/agreement-templates", response_model=list[AgreementTemplateListItemOut])
def list_admin_agreement_templates(
    request: Request,
    template_type: TemplateType | None = Query(default=None),
    status_value: TemplateStatus | None = Query(default=None, alias="status"),
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> list[AgreementTemplateListItemOut]:
    admin = _require_super_admin(admin)
    rows = list_agreement_templates(db=db, template_type=template_type, status_value=status_value)
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_AGREEMENT_TEMPLATE_LIST",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="AGREEMENT_TEMPLATE",
        detail_json={
            "count": len(rows),
            "template_type": template_type.value if template_type else None,
            "status": status_value.value if status_value else None,
        },
        auto_commit=True,
    )
    return rows


@router.post("/agreement-templates", response_model=AgreementTemplateDetailOut, status_code=status.HTTP_201_CREATED)
def create_admin_agreement_template(
    payload: AgreementTemplateCreateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> AgreementTemplateDetailOut:
    admin = _require_super_admin(admin)
    row = create_agreement_template(db=db, payload=payload, current_user=admin.user)
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_AGREEMENT_TEMPLATE_CREATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="AGREEMENT_TEMPLATE",
        entity_id=str(row.id),
        detail_json={
            "template_type": row.template_type.value,
            "template_code": row.template_code,
            "is_default": row.is_default,
        },
    )
    db.commit()
    db.refresh(row)
    return serialize_agreement_template_detail(db=db, template=row)


@router.get("/agreement-templates/{template_id}", response_model=AgreementTemplateDetailOut)
def get_admin_agreement_template(
    template_id: int,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> AgreementTemplateDetailOut:
    admin = _require_super_admin(admin)
    row = get_agreement_template_or_404(db=db, template_id=template_id)
    result = serialize_agreement_template_detail(db=db, template=row)
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_AGREEMENT_TEMPLATE_DETAIL",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="AGREEMENT_TEMPLATE",
        entity_id=str(row.id),
        auto_commit=True,
    )
    return result


@router.patch("/agreement-templates/{template_id}", response_model=AgreementTemplateDetailOut)
def update_admin_agreement_template(
    template_id: int,
    payload: AgreementTemplateUpdateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> AgreementTemplateDetailOut:
    admin = _require_super_admin(admin)
    row = get_agreement_template_or_404(db=db, template_id=template_id)
    row = update_agreement_template(db=db, template=row, payload=payload, current_user=admin.user)
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_AGREEMENT_TEMPLATE_UPDATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="AGREEMENT_TEMPLATE",
        entity_id=str(row.id),
        detail_json={
            "template_name": row.template_name,
            "status": row.status.value,
        },
    )
    db.commit()
    db.refresh(row)
    return serialize_agreement_template_detail(db=db, template=row)


@router.patch("/agreement-templates/{template_id}/status", response_model=AgreementTemplateDetailOut)
def update_admin_agreement_template_status(
    template_id: int,
    payload: AgreementTemplateStatusUpdateRequest,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> AgreementTemplateDetailOut:
    admin = _require_super_admin(admin)
    row = get_agreement_template_or_404(db=db, template_id=template_id)
    before_status = row.status.value
    row = update_agreement_template_status(db=db, template=row, status_value=payload.status, current_user=admin.user)
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_AGREEMENT_TEMPLATE_STATUS_UPDATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="AGREEMENT_TEMPLATE",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
    )
    db.commit()
    db.refresh(row)
    return serialize_agreement_template_detail(db=db, template=row)


@router.post("/agreement-templates/{template_id}/set-default", response_model=AgreementTemplateDetailOut)
def set_admin_agreement_template_default(
    template_id: int,
    request: Request,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> AgreementTemplateDetailOut:
    admin = _require_super_admin(admin)
    row = get_agreement_template_or_404(db=db, template_id=template_id)
    row = set_agreement_template_default(db=db, template=row, current_user=admin.user)
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_AGREEMENT_TEMPLATE_SET_DEFAULT",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="AGREEMENT_TEMPLATE",
        entity_id=str(row.id),
        detail_json={"template_type": row.template_type.value},
    )
    db.commit()
    db.refresh(row)
    return serialize_agreement_template_detail(db=db, template=row)
