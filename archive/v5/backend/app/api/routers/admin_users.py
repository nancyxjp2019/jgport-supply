from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import BRIDGE_ADMIN_USERNAME, AdminOperator, get_admin_operator
from app.core.config import get_settings
from app.core.security import generate_activation_code
from app.db.session import get_db
from app.models.activation_code import ActivationCode
from app.models.user import User, UserRole, UserStatus
from app.models.v5_domain import Company, CompanyType
from app.schemas.user import ActivationLinkOut, UserCreate, UserOut, UserProfileUpdate, UserRoleUpdate, UserStatusUpdate
from app.services.business_log_service import write_business_log

router = APIRouter(prefix="/admin", tags=["admin-users"])

ROLE_COMPANY_TYPE_RULES: dict[UserRole, set[CompanyType]] = {
    UserRole.CUSTOMER: {CompanyType.CUSTOMER},
    UserRole.SUPPLIER: {CompanyType.SUPPLIER},
    UserRole.OPERATOR: {CompanyType.OPERATOR},
    UserRole.WAREHOUSE: {CompanyType.WAREHOUSE},
    UserRole.FINANCE: {CompanyType.OPERATOR},
    UserRole.ADMIN: {CompanyType.OPERATOR},
}

REQUIRED_COMPANY_ROLES = {
    UserRole.CUSTOMER,
    UserRole.SUPPLIER,
    UserRole.OPERATOR,
    UserRole.WAREHOUSE,
}


def _validate_user_company_binding(
    db: Session,
    *,
    role: UserRole,
    company_id: int | None,
) -> Company | None:
    if company_id is None:
        if role in REQUIRED_COMPANY_ROLES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="company_binding_required_for_role")
        return None

    company = db.scalar(select(Company).where(Company.id == company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company_not_found")
    if not company.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="company_not_active")

    allowed_types = ROLE_COMPANY_TYPE_RULES[role]
    if company.company_type not in allowed_types:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user_company_role_mismatch")
    return company


@router.get("/users", response_model=list[UserOut])
def list_users(
    request: Request,
    role: UserRole | None = Query(default=None),
    status_value: UserStatus | None = Query(default=None, alias="status"),
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    if status_value is not None:
        query = query.where(User.status == status_value)

    users = db.scalars(query.order_by(User.id.desc())).all()
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_USER_LIST",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="USER",
        detail_json={
            "count": len(users),
            "role_filter": role.value if role else None,
            "status_filter": status_value.value if status_value else None,
        },
        auto_commit=True,
    )
    return [UserOut.model_validate(user) for user in users]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    payload: UserCreate,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> UserOut:
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists is not None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_USER_CREATE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="USER",
            reason="用户名已存在",
            detail_json={"username": payload.username},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username_exists")

    company = _validate_user_company_binding(db=db, role=payload.role, company_id=payload.company_id)
    company_name_snapshot = company.company_name if company is not None else None

    user = User(
        username=payload.username,
        display_name=payload.display_name,
        role=payload.role,
        status=payload.status,
        customer_id=payload.customer_id,
        company_id=company.id if company is not None else None,
        company_name_snapshot=company_name_snapshot,
    )
    db.add(user)
    db.flush()
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_USER_CREATE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="USER",
        entity_id=str(user.id),
        detail_json={
            "username": user.username,
            "role": user.role.value,
            "status": user.status.value,
            "company_id": user.company_id,
        },
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}/status", response_model=UserOut)
def update_user_status(
    request: Request,
    user_id: int,
    payload: UserStatusUpdate,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_USER_UPDATE_STATUS",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="USER",
            entity_id=str(user_id),
            reason="用户不存在",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    before_status = user.status.value
    user.status = payload.status
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_USER_UPDATE_STATUS",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="USER",
        entity_id=str(user.id),
        before_status=before_status,
        after_status=user.status.value,
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    request: Request,
    user_id: int,
    payload: UserRoleUpdate,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_USER_UPDATE_ROLE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="USER",
            entity_id=str(user_id),
            reason="用户不存在",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    if user.username == BRIDGE_ADMIN_USERNAME:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_USER_UPDATE_ROLE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="USER",
            entity_id=str(user.id),
            reason="桥接管理员账号角色不可修改",
            detail_json={"username": user.username},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="bridge_user_role_locked")

    company = _validate_user_company_binding(db=db, role=payload.role, company_id=user.company_id)
    before_role = user.role.value
    user.role = payload.role
    user.company_name_snapshot = company.company_name if company is not None else None
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_USER_UPDATE_ROLE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="USER",
        entity_id=str(user.id),
        detail_json={
            "username": user.username,
            "before_role": before_role,
            "after_role": user.role.value,
        },
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}/profile", response_model=UserOut)
def update_user_profile(
    request: Request,
    user_id: int,
    payload: UserProfileUpdate,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_USER_UPDATE_PROFILE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="USER",
            entity_id=str(user_id),
            reason="用户不存在",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    if user.username == BRIDGE_ADMIN_USERNAME:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_USER_UPDATE_PROFILE",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="USER",
            entity_id=str(user.id),
            reason="桥接管理员账号信息不可修改",
            detail_json={"username": user.username},
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="bridge_user_profile_locked")

    has_username_field = "username" in payload.model_fields_set
    has_display_name_field = "display_name" in payload.model_fields_set
    has_company_field = "company_id" in payload.model_fields_set
    if not has_username_field and not has_display_name_field and not has_company_field:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="profile_fields_required")

    before_username = user.username
    before_display_name = user.display_name
    before_company_id = user.company_id
    changed_fields: dict[str, str | int | None] = {}

    if has_username_field:
        if payload.username is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="username_required")

        next_username = payload.username.strip()
        if len(next_username) < 2:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="username_too_short")

        if next_username == BRIDGE_ADMIN_USERNAME:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username_reserved")

        exists = db.scalar(select(User).where(User.username == next_username, User.id != user.id))
        if exists is not None:
            write_business_log(
                db=db,
                request=request,
                action="ADMIN_USER_UPDATE_PROFILE",
                result="FAILED",
                user=admin.user,
                actor_user_id=admin.actor_id,
                role=admin.role,
                entity_type="USER",
                entity_id=str(user.id),
                reason="用户名已存在",
                detail_json={"username": next_username},
                auto_commit=True,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username_exists")

        if next_username != user.username:
            user.username = next_username
            changed_fields["username"] = next_username

    if has_display_name_field:
        next_display_name = (payload.display_name or "").strip() or None
        if next_display_name != user.display_name:
            user.display_name = next_display_name
            changed_fields["display_name"] = next_display_name

    if has_company_field:
        if payload.company_id is None:
            company = _validate_user_company_binding(db=db, role=user.role, company_id=None)
            if user.company_id is not None:
                user.company_id = None
                user.company_name_snapshot = company.company_name if company is not None else None
                changed_fields["company_id"] = None
        else:
            company = _validate_user_company_binding(db=db, role=user.role, company_id=payload.company_id)
            if user.company_id != company.id or user.company_name_snapshot != company.company_name:
                user.company_id = company.id
                user.company_name_snapshot = company.company_name
                changed_fields["company_id"] = company.id

    if not changed_fields:
        return UserOut.model_validate(user)

    write_business_log(
        db=db,
        request=request,
        action="ADMIN_USER_UPDATE_PROFILE",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="USER",
        entity_id=str(user.id),
        detail_json={
            "before_username": before_username,
            "after_username": user.username,
            "before_display_name": before_display_name,
            "after_display_name": user.display_name,
            "before_company_id": before_company_id,
            "after_company_id": user.company_id,
            "changed_fields": changed_fields,
        },
    )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/users/{user_id}/activation-link", response_model=ActivationLinkOut)
def create_activation_link(
    request: Request,
    user_id: int,
    admin: AdminOperator = Depends(get_admin_operator),
    db: Session = Depends(get_db),
) -> ActivationLinkOut:
    settings = get_settings()
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        write_business_log(
            db=db,
            request=request,
            action="ADMIN_USER_CREATE_ACTIVATION_LINK",
            result="FAILED",
            user=admin.user,
            actor_user_id=admin.actor_id,
            role=admin.role,
            entity_type="USER",
            entity_id=str(user_id),
            reason="用户不存在",
            auto_commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    code = generate_activation_code()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.activation_code_expire_minutes)

    activation = ActivationCode(
        user_id=user.id,
        code=code,
        expires_at=expires_at,
        created_by=admin.actor_id,
    )
    db.add(activation)
    write_business_log(
        db=db,
        request=request,
        action="ADMIN_USER_CREATE_ACTIVATION_LINK",
        result="SUCCESS",
        user=admin.user,
        actor_user_id=admin.actor_id,
        role=admin.role,
        entity_type="USER",
        entity_id=str(user.id),
        detail_json={
            "expires_at": expires_at.isoformat(),
            "code_tail": code[-4:],
        },
    )
    db.commit()

    activation_url = f"{settings.activation_link_base_url}?code={code}&uid={user.id}"
    return ActivationLinkOut(
        user_id=user.id,
        code=code,
        expires_at=expires_at,
        activation_url=activation_url,
    )
