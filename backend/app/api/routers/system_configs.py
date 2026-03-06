from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, require_actor
from app.db.session import get_db
from app.models.business_audit_log import BusinessAuditLog
from app.models.threshold_config_version import ThresholdConfigVersion
from app.schemas.threshold import ThresholdConfigPublishRequest, ThresholdConfigResponse

router = APIRouter(prefix="/system-configs", tags=["system-configs"])
admin_actor_dependency = require_actor(
    allowed_roles={"admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)


@router.get("/thresholds", response_model=ThresholdConfigResponse)
def get_thresholds(
    _: AuthenticatedActor = Depends(admin_actor_dependency),
    db: Session = Depends(get_db),
) -> ThresholdConfigResponse:
    current = db.scalar(
        select(ThresholdConfigVersion)
        .where(ThresholdConfigVersion.is_active.is_(True))
        .order_by(ThresholdConfigVersion.version.desc())
        .limit(1)
    )
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到生效中的阈值配置")

    return ThresholdConfigResponse(
        version=current.version,
        threshold_release=current.threshold_release,
        threshold_over_exec=current.threshold_over_exec,
        status=current.status,
        message="查询成功",
    )


@router.put("/thresholds", response_model=ThresholdConfigResponse)
def publish_thresholds(
    payload: ThresholdConfigPublishRequest,
    actor: AuthenticatedActor = Depends(admin_actor_dependency),
    db: Session = Depends(get_db),
) -> ThresholdConfigResponse:
    if payload.threshold_release > payload.threshold_over_exec:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="保证金放行阈值不能大于合同超量履约阈值",
        )

    current = db.scalar(
        select(ThresholdConfigVersion)
        .where(ThresholdConfigVersion.is_active.is_(True))
        .order_by(ThresholdConfigVersion.version.desc())
        .limit(1)
    )
    next_version = db.scalar(select(func.coalesce(func.max(ThresholdConfigVersion.version), 0))) + 1
    before_payload = _build_before_payload(current)

    if current is not None:
        current.is_active = False
        current.status = "停用"

    new_config = ThresholdConfigVersion(
        version=next_version,
        threshold_release=_normalize_threshold(payload.threshold_release),
        threshold_over_exec=_normalize_threshold(payload.threshold_over_exec),
        status="生效",
        is_active=True,
        reason=payload.reason,
        created_by=actor.user_id,
    )
    db.add(new_config)
    db.add(
        BusinessAuditLog(
            event_code="M1-THRESHOLD-PUBLISH",
            biz_type="threshold_config",
            biz_id=f"thresholds:v{next_version}",
            operator_id=actor.user_id,
            before_json=before_payload,
            after_json={
                "version": next_version,
                "threshold_release": str(new_config.threshold_release),
                "threshold_over_exec": str(new_config.threshold_over_exec),
                "status": new_config.status,
            },
            extra_json={"reason": payload.reason},
        )
    )
    db.commit()
    db.refresh(new_config)
    return ThresholdConfigResponse(
        version=new_config.version,
        threshold_release=new_config.threshold_release,
        threshold_over_exec=new_config.threshold_over_exec,
        status=new_config.status,
        message="阈值配置已发布",
    )


def _normalize_threshold(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"))


def _build_before_payload(current: ThresholdConfigVersion | None) -> dict:
    if current is None:
        return {}
    return {
        "version": current.version,
        "threshold_release": str(current.threshold_release),
        "threshold_over_exec": str(current.threshold_over_exec),
        "status": current.status,
    }
