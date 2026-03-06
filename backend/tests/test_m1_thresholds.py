from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.services.threshold_service import get_active_threshold_snapshot

client = TestClient(app)


def test_thresholds_require_admin_identity(auth_headers) -> None:
    response = client.get(
        "/api/v1/system-configs/thresholds",
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE",
            role_code="finance",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前角色无权访问该接口"


def test_threshold_release_cannot_exceed_over_exec(auth_headers) -> None:
    response = client.put(
        "/api/v1/system-configs/thresholds",
        json={
            "threshold_release": 1.060,
            "threshold_over_exec": 1.050,
            "reason": "测试非法阈值",
        },
        headers=auth_headers(),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "保证金放行阈值不能大于合同超量履约阈值"


def test_publish_threshold_version_and_query(auth_headers) -> None:
    headers = auth_headers()
    before_response = client.get("/api/v1/system-configs/thresholds", headers=headers)
    assert before_response.status_code == 200
    before_body = before_response.json()

    next_release = Decimal(str(before_body["threshold_release"])) + Decimal("0.001")
    next_over_exec = max(
        Decimal(str(before_body["threshold_over_exec"])),
        next_release,
    )

    publish_response = client.put(
        "/api/v1/system-configs/thresholds",
        json={
            "threshold_release": float(next_release),
            "threshold_over_exec": float(next_over_exec),
            "reason": "测试发布新版本",
        },
        headers=headers,
    )
    assert publish_response.status_code == 200
    publish_body = publish_response.json()
    assert publish_body["version"] == before_body["version"] + 1
    assert publish_body["message"] == "阈值配置已发布"

    after_response = client.get("/api/v1/system-configs/thresholds", headers=headers)
    assert after_response.status_code == 200
    after_body = after_response.json()
    assert after_body["version"] == publish_body["version"]
    assert Decimal(str(after_body["threshold_release"])) == next_release
    assert Decimal(str(after_body["threshold_over_exec"])) == next_over_exec


def test_active_threshold_snapshot_matches_current_version(auth_headers) -> None:
    headers = auth_headers()
    response = client.get("/api/v1/system-configs/thresholds", headers=headers)
    assert response.status_code == 200
    body = response.json()

    db: Session = SessionLocal()
    try:
        snapshot = get_active_threshold_snapshot(db)
        assert snapshot is not None
        assert snapshot.version == body["version"]
        assert Decimal(str(snapshot.threshold_release)) == Decimal(str(body["threshold_release"]))
        assert Decimal(str(snapshot.threshold_over_exec)) == Decimal(str(body["threshold_over_exec"]))
    finally:
        db.close()
