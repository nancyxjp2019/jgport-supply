from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.services.audit_log_service import write_audit_log_with_retry

client = TestClient(app)


def test_audit_log_write_requires_admin_role(auth_headers) -> None:
    response = client.post(
        "/api/v1/audit/logs",
        json={
            "event_code": "M1-T07",
            "biz_type": "test_case",
            "biz_id": "CODEX-TEST-AUDIT-FORBIDDEN",
            "before_json": {},
            "after_json": {},
            "extra_json": {},
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE",
            role_code="finance",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前角色无权访问该接口"


def test_create_and_query_audit_log_by_biz_id(auth_headers) -> None:
    biz_id = f"CODEX-TEST-{uuid4().hex[:12]}"
    admin_headers = auth_headers()
    create_response = client.post(
        "/api/v1/audit/logs",
        json={
            "event_code": "M1-T07",
            "biz_type": "test_case",
            "biz_id": biz_id,
            "before_json": {"status": "草稿"},
            "after_json": {"status": "生效"},
            "extra_json": {"note": "审计日志查询测试"},
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 200
    assert create_response.json()["message"] == "审计日志写入成功"

    query_response = client.get(
        "/api/v1/audit/logs",
        params={"biz_id": biz_id, "limit": 5},
        headers=auth_headers(
            user_id="CODEX-TEST-OPS",
            role_code="operations",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert query_response.status_code == 200
    items = query_response.json()["items"]
    assert len(items) >= 1
    assert items[0]["biz_id"] == biz_id
    assert items[0]["operator_id"] == "CODEX-TEST-ADMIN"


def test_audit_retry_service_can_succeed_after_transient_failures() -> None:
    store: list[object] = []
    state = {"remaining_failures": 2}

    class FakeSession:
        def __init__(self) -> None:
            self._obj = None

        def add(self, obj: object) -> None:
            self._obj = obj

        def commit(self) -> None:
            if state["remaining_failures"] > 0:
                state["remaining_failures"] -= 1
                raise SQLAlchemyError("模拟瞬时失败")
            if self._obj is not None:
                setattr(self._obj, "id", len(store) + 1)
                store.append(self._obj)

        def refresh(self, obj: object) -> None:
            _ = obj

        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    def fake_session_factory() -> FakeSession:
        return FakeSession()

    log = write_audit_log_with_retry(
        fake_session_factory,
        payload={
            "event_code": "M1-T08",
            "biz_type": "test_case",
            "biz_id": "retry-case",
            "operator_id": "tester",
            "before_json": {},
            "after_json": {"retry": "success"},
            "extra_json": {},
        },
        max_retries=3,
    )
    assert getattr(log, "id") == 1
    assert len(store) == 1
