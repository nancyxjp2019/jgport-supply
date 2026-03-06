from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.threshold_config_version import ThresholdConfigVersion


def get_active_threshold_snapshot(db: Session) -> ThresholdConfigVersion | None:
    return db.scalar(
        select(ThresholdConfigVersion)
        .where(ThresholdConfigVersion.is_active.is_(True))
        .order_by(ThresholdConfigVersion.version.desc())
        .limit(1)
    )
