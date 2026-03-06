from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_threshold_release_cannot_exceed_over_exec() -> None:
    response = client.put(
        "/api/v1/system-configs/thresholds",
        json={
            "threshold_release": 1.060,
            "threshold_over_exec": 1.050,
            "reason": "测试非法阈值",
            "operator_id": "tester",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "保证金放行阈值不能大于合同超量履约阈值"


def test_publish_threshold_version_and_query() -> None:
    before_response = client.get("/api/v1/system-configs/thresholds")
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
            "operator_id": "tester",
        },
    )
    assert publish_response.status_code == 200
    publish_body = publish_response.json()
    assert publish_body["version"] == before_body["version"] + 1
    assert publish_body["message"] == "阈值配置已发布"

    after_response = client.get("/api/v1/system-configs/thresholds")
    assert after_response.status_code == 200
    after_body = after_response.json()
    assert after_body["version"] == publish_body["version"]
    assert Decimal(str(after_body["threshold_release"])) == next_release
    assert Decimal(str(after_body["threshold_over_exec"])) == next_over_exec
