from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.v5_domain import AgreementTemplate, AgreementTemplateVersion, TemplateStatus, TemplateType
from app.schemas.v5_template import (
    AgreementTemplateCreateRequest,
    AgreementTemplateContentOut,
    AgreementTemplateDetailOut,
    AgreementTemplateListItemOut,
    AgreementTemplateUpdateRequest,
)


def _serialize_content(row: AgreementTemplateVersion) -> AgreementTemplateContentOut:
    return AgreementTemplateContentOut(
        template_title=row.template_title,
        template_content_json=row.template_content_json or {},
        placeholder_schema_json=row.placeholder_schema_json or {},
        render_config_json=row.render_config_json or {},
    )


def _serialize_template(row: AgreementTemplate, current_content: AgreementTemplateVersion) -> AgreementTemplateDetailOut:
    return AgreementTemplateDetailOut(
        id=row.id,
        template_type=row.template_type,
        template_code=row.template_code,
        template_name=row.template_name,
        is_default=row.is_default,
        status=row.status,
        remark=row.remark,
        created_by=row.created_by,
        updated_by=row.updated_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        template_title=current_content.template_title,
        template_content_json=current_content.template_content_json or {},
        placeholder_schema_json=current_content.placeholder_schema_json or {},
        render_config_json=current_content.render_config_json or {},
    )


def _normalize_template_code(raw_value: str) -> str:
    value = str(raw_value or "").strip()
    if not value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="template_code_empty")
    return value


def _ensure_default_uniqueness(db: Session, *, template_type: TemplateType, current_template_id: int | None = None) -> None:
    query = select(AgreementTemplate).where(
        AgreementTemplate.template_type == template_type,
        AgreementTemplate.is_default.is_(True),
    )
    if current_template_id is not None:
        query = query.where(AgreementTemplate.id != current_template_id)
    rows = db.scalars(query).all()
    for row in rows:
        row.is_default = False


def get_agreement_template_or_404(db: Session, *, template_id: int) -> AgreementTemplate:
    row = db.scalar(select(AgreementTemplate).where(AgreementTemplate.id == template_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agreement_template_not_found")
    return row


def get_current_template_version(db: Session, *, template: AgreementTemplate) -> AgreementTemplateVersion:
    row = db.scalar(
        select(AgreementTemplateVersion).where(
            AgreementTemplateVersion.template_id == template.id,
            AgreementTemplateVersion.version_no == template.current_version_no,
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agreement_template_version_missing")
    return row


def list_agreement_templates(
    db: Session,
    *,
    template_type: TemplateType | None,
    status_value: TemplateStatus | None,
) -> list[AgreementTemplateListItemOut]:
    query: Select[tuple[AgreementTemplate]] = select(AgreementTemplate)
    if template_type is not None:
        query = query.where(AgreementTemplate.template_type == template_type)
    if status_value is not None:
        query = query.where(AgreementTemplate.status == status_value)
    rows = db.scalars(
        query.order_by(
            AgreementTemplate.template_type.asc(),
            AgreementTemplate.is_default.desc(),
            AgreementTemplate.template_name.asc(),
            AgreementTemplate.id.asc(),
        )
    ).all()
    return [
        AgreementTemplateListItemOut(
            id=row.id,
            template_type=row.template_type,
            template_code=row.template_code,
            template_name=row.template_name,
            is_default=row.is_default,
            status=row.status,
            remark=row.remark,
            created_by=row.created_by,
            updated_by=row.updated_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def create_agreement_template(
    db: Session,
    *,
    payload: AgreementTemplateCreateRequest,
    current_user: User,
) -> AgreementTemplate:
    template_code = _normalize_template_code(payload.template_code)
    exists = db.scalar(select(AgreementTemplate.id).where(AgreementTemplate.template_code == template_code))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agreement_template_code_exists")

    if payload.is_default:
        _ensure_default_uniqueness(db=db, template_type=payload.template_type)

    row = AgreementTemplate(
        template_type=payload.template_type,
        template_code=template_code,
        template_name=payload.template_name,
        is_default=payload.is_default,
        status=payload.status,
        current_version_no=1,
        remark=payload.remark,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(row)
    db.flush()
    version = AgreementTemplateVersion(
        template_id=row.id,
        version_no=1,
        template_title=payload.template_title,
        template_content_json=payload.template_content_json,
        placeholder_schema_json=payload.placeholder_schema_json,
        render_config_json=payload.render_config_json,
        created_by=current_user.id,
    )
    db.add(version)
    db.flush()
    return row


def update_agreement_template(
    db: Session,
    *,
    template: AgreementTemplate,
    payload: AgreementTemplateUpdateRequest,
    current_user: User,
) -> AgreementTemplate:
    changed = False
    if "template_name" in payload.model_fields_set and payload.template_name is not None and payload.template_name != template.template_name:
        template.template_name = payload.template_name
        changed = True
    if "remark" in payload.model_fields_set:
        next_remark = payload.remark
        if next_remark != template.remark:
            template.remark = next_remark
            changed = True

    content_fields = {"template_title", "template_content_json", "placeholder_schema_json", "render_config_json"}
    if payload.model_fields_set & content_fields:
        current_version = get_current_template_version(db=db, template=template)
        if "template_title" in payload.model_fields_set:
            current_version.template_title = payload.template_title
        if "template_content_json" in payload.model_fields_set and payload.template_content_json is not None:
            current_version.template_content_json = payload.template_content_json
        if "placeholder_schema_json" in payload.model_fields_set and payload.placeholder_schema_json is not None:
            current_version.placeholder_schema_json = payload.placeholder_schema_json
        if "render_config_json" in payload.model_fields_set and payload.render_config_json is not None:
            current_version.render_config_json = payload.render_config_json
        changed = True

    if changed:
        template.updated_by = current_user.id
        db.flush()
    return template


def update_agreement_template_status(
    db: Session,
    *,
    template: AgreementTemplate,
    status_value: TemplateStatus,
    current_user: User,
) -> AgreementTemplate:
    template.status = status_value
    if status_value == TemplateStatus.DISABLED and template.is_default:
        template.is_default = False
    template.updated_by = current_user.id
    db.flush()
    return template


def set_agreement_template_default(
    db: Session,
    *,
    template: AgreementTemplate,
    current_user: User,
) -> AgreementTemplate:
    if template.status != TemplateStatus.ENABLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agreement_template_not_enabled")
    _ensure_default_uniqueness(db=db, template_type=template.template_type, current_template_id=template.id)
    template.is_default = True
    template.updated_by = current_user.id
    db.flush()
    return template


def serialize_agreement_template_detail(db: Session, *, template: AgreementTemplate) -> AgreementTemplateDetailOut:
    current_version = get_current_template_version(db=db, template=template)
    return _serialize_template(template, current_content=current_version)
