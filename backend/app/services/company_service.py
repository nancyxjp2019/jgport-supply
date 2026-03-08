from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth_actor import AuthenticatedActor
from app.models.business_audit_log import BusinessAuditLog
from app.models.company_profile import CompanyProfile


def list_company_profiles(
    db: Session,
    *,
    company_type: str | None = None,
    status_text: str | None = None,
) -> tuple[list[dict[str, object]], int]:
    statement = select(CompanyProfile)
    if company_type:
        statement = statement.where(CompanyProfile.company_type == company_type)
    if status_text:
        statement = statement.where(CompanyProfile.status == status_text)
    statement = statement.order_by(
        CompanyProfile.company_type.asc(), CompanyProfile.company_id.asc()
    )
    companies = list(db.scalars(statement).all())
    return _serialize_company_list(db, companies), len(companies)


def get_company_profile(db: Session, company_id: str) -> dict[str, object]:
    company = _load_company_or_raise(db, company_id)
    return _serialize_company_detail(db, company)


def create_company_profile(
    db: Session,
    *,
    company_id: str,
    company_name: str,
    company_type: str,
    parent_company_id: str | None,
    remark: str | None,
    actor: AuthenticatedActor,
) -> dict[str, object]:
    normalized_company_id = _normalize_required_text(company_id, "公司编码不能为空")
    if db.get(CompanyProfile, normalized_company_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="公司编码已存在"
        )

    normalized_company_name = _normalize_required_text(company_name, "公司名称不能为空")
    normalized_remark = _normalize_optional_text(remark)
    parent_company = _resolve_parent_company(
        db,
        company_type=company_type,
        parent_company_id=parent_company_id,
        current_company_id=None,
    )

    company = CompanyProfile(
        company_id=normalized_company_id,
        company_name=normalized_company_name,
        company_type=company_type,
        parent_company_id=parent_company.company_id if parent_company else None,
        status="启用",
        is_active=True,
        remark=normalized_remark,
        created_by=actor.user_id,
        updated_by=actor.user_id,
    )
    db.add(company)
    db.add(
        _build_audit_log(
            event_code="G1-COMPANY-CREATE",
            actor=actor,
            company_id=company.company_id,
            before_json={},
            after_json=_snapshot_company(
                company,
                parent_company_name=parent_company.company_name
                if parent_company
                else None,
                child_company_count=0,
            ),
            extra_json={"reason": "创建公司档案"},
        )
    )
    db.commit()
    db.refresh(company)
    return _serialize_company_detail(db, company, message="公司创建成功")


def update_company_profile(
    db: Session,
    *,
    company_id: str,
    company_name: str,
    parent_company_id: str | None,
    remark: str | None,
    actor: AuthenticatedActor,
) -> dict[str, object]:
    company = _load_company_or_raise(db, company_id)
    parent_company = _resolve_parent_company(
        db,
        company_type=company.company_type,
        parent_company_id=parent_company_id,
        current_company_id=company.company_id,
    )
    before_json = _snapshot_company(
        company,
        parent_company_name=_get_parent_company_name(db, company.parent_company_id),
        child_company_count=_count_active_child_companies(db, company.company_id),
    )

    company.company_name = _normalize_required_text(company_name, "公司名称不能为空")
    company.parent_company_id = parent_company.company_id if parent_company else None
    company.remark = _normalize_optional_text(remark)
    company.updated_by = actor.user_id

    db.add(
        _build_audit_log(
            event_code="G1-COMPANY-UPDATE",
            actor=actor,
            company_id=company.company_id,
            before_json=before_json,
            after_json=_snapshot_company(
                company,
                parent_company_name=parent_company.company_name
                if parent_company
                else None,
                child_company_count=_count_active_child_companies(
                    db, company.company_id
                ),
            ),
            extra_json={"reason": "编辑公司档案"},
        )
    )
    db.commit()
    db.refresh(company)
    return _serialize_company_detail(db, company, message="公司信息已更新")


def change_company_profile_status(
    db: Session,
    *,
    company_id: str,
    enabled: bool,
    reason: str,
    actor: AuthenticatedActor,
) -> dict[str, object]:
    company = _load_company_or_raise(db, company_id)
    normalized_reason = _normalize_required_text(reason, "状态变更原因不能为空")
    if enabled:
        parent_company = _resolve_parent_company(
            db,
            company_type=company.company_type,
            parent_company_id=company.parent_company_id,
            current_company_id=company.company_id,
        )
        next_status = "启用"
        next_active = True
        message = "公司已启用"
    else:
        if _count_active_child_companies(db, company.company_id) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="当前公司仍存在启用中的下级公司，禁止停用",
            )
        parent_company = None
        next_status = "停用"
        next_active = False
        message = "公司已停用"

    if company.is_active == next_active and company.status == next_status:
        return _serialize_company_detail(db, company, message=message)

    before_json = _snapshot_company(
        company,
        parent_company_name=_get_parent_company_name(db, company.parent_company_id),
        child_company_count=_count_active_child_companies(db, company.company_id),
    )
    company.is_active = next_active
    company.status = next_status
    company.updated_by = actor.user_id
    db.add(
        _build_audit_log(
            event_code="G1-COMPANY-STATUS",
            actor=actor,
            company_id=company.company_id,
            before_json=before_json,
            after_json=_snapshot_company(
                company,
                parent_company_name=_get_parent_company_name(
                    db, company.parent_company_id
                ),
                child_company_count=_count_active_child_companies(
                    db, company.company_id
                ),
            ),
            extra_json={"reason": normalized_reason},
        )
    )
    db.commit()
    db.refresh(company)
    return _serialize_company_detail(db, company, message=message)


def _resolve_parent_company(
    db: Session,
    *,
    company_type: str,
    parent_company_id: str | None,
    current_company_id: str | None,
) -> CompanyProfile | None:
    normalized_parent_company_id = _normalize_optional_text(parent_company_id)
    if company_type == "operator_company":
        if normalized_parent_company_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="运营商公司不能绑定上级公司",
            )
        return None

    if not normalized_parent_company_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="非运营商公司必须绑定归属运营商",
        )
    if current_company_id and normalized_parent_company_id == current_company_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="公司不能归属到自身",
        )

    parent_company = db.get(CompanyProfile, normalized_parent_company_id)
    if parent_company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="归属运营商公司不存在"
        )
    if parent_company.company_type != "operator_company":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="归属公司必须是运营商公司",
        )
    if not parent_company.is_active or parent_company.status != "启用":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="归属运营商公司必须处于启用状态",
        )
    return parent_company


def _serialize_company_list(
    db: Session, companies: list[CompanyProfile]
) -> list[dict[str, object]]:
    parent_name_map = _load_parent_name_map(db, companies)
    child_count_map = _load_child_count_map(db, companies)
    return [
        _snapshot_company(
            company,
            parent_company_name=parent_name_map.get(company.parent_company_id),
            child_company_count=child_count_map.get(company.company_id, 0),
        )
        for company in companies
    ]


def _serialize_company_detail(
    db: Session,
    company: CompanyProfile,
    *,
    message: str = "查询成功",
) -> dict[str, object]:
    payload = _snapshot_company(
        company,
        parent_company_name=_get_parent_company_name(db, company.parent_company_id),
        child_company_count=_count_active_child_companies(db, company.company_id),
    )
    payload["created_by"] = company.created_by
    payload["updated_by"] = company.updated_by
    payload["message"] = message
    return payload


def _snapshot_company(
    company: CompanyProfile,
    *,
    parent_company_name: str | None,
    child_company_count: int,
) -> dict[str, object]:
    return {
        "company_id": company.company_id,
        "company_name": company.company_name,
        "company_type": company.company_type,
        "parent_company_id": company.parent_company_id,
        "parent_company_name": parent_company_name,
        "status": company.status,
        "is_active": company.is_active,
        "remark": company.remark,
        "child_company_count": child_company_count,
        "created_at": _serialize_datetime(company.created_at),
        "updated_at": _serialize_datetime(company.updated_at),
    }


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _load_parent_name_map(
    db: Session, companies: list[CompanyProfile]
) -> dict[str, str]:
    parent_ids = sorted(
        {
            company.parent_company_id
            for company in companies
            if company.parent_company_id
        }
    )
    if not parent_ids:
        return {}
    rows = db.execute(
        select(CompanyProfile.company_id, CompanyProfile.company_name).where(
            CompanyProfile.company_id.in_(parent_ids)
        )
    ).all()
    return {row.company_id: row.company_name for row in rows}


def _load_child_count_map(
    db: Session, companies: list[CompanyProfile]
) -> dict[str, int]:
    company_ids = [company.company_id for company in companies]
    if not company_ids:
        return {}
    rows = db.execute(
        select(CompanyProfile.parent_company_id, func.count())
        .where(
            CompanyProfile.parent_company_id.in_(company_ids),
            CompanyProfile.is_active.is_(True),
        )
        .group_by(CompanyProfile.parent_company_id)
    ).all()
    return {str(row[0]): int(row[1]) for row in rows if row[0] is not None}


def _get_parent_company_name(db: Session, parent_company_id: str | None) -> str | None:
    if not parent_company_id:
        return None
    parent_company = db.get(CompanyProfile, parent_company_id)
    return parent_company.company_name if parent_company else None


def _count_active_child_companies(db: Session, company_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CompanyProfile)
            .where(
                CompanyProfile.parent_company_id == company_id,
                CompanyProfile.is_active.is_(True),
            )
        )
        or 0
    )


def _load_company_or_raise(db: Session, company_id: str) -> CompanyProfile:
    normalized_company_id = _normalize_required_text(company_id, "公司编码不能为空")
    company = db.get(CompanyProfile, normalized_company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公司不存在")
    return company


def _normalize_required_text(value: str | None, detail: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail
        )
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _build_audit_log(
    *,
    event_code: str,
    actor: AuthenticatedActor,
    company_id: str,
    before_json: dict[str, object],
    after_json: dict[str, object],
    extra_json: dict[str, object],
) -> BusinessAuditLog:
    return BusinessAuditLog(
        event_code=event_code,
        biz_type="company_profile",
        biz_id=company_id,
        operator_id=actor.user_id,
        before_json=before_json,
        after_json=after_json,
        extra_json=extra_json,
    )
