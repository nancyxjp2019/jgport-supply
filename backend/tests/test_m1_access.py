from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_access_check_requires_authenticated_identity() -> None:
    response = client.post(
        "/api/v1/access/check",
        json={"target_client_type": "admin_web"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "未认证身份，禁止访问"


def test_customer_cannot_login_admin_web(auth_headers) -> None:
    response = client.post(
        "/api/v1/access/check",
        json={"target_client_type": "admin_web"},
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER",
            role_code="customer",
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前角色不允许登录该端"


def test_operations_can_login_admin_web(auth_headers) -> None:
    response = client.post(
        "/api/v1/access/check",
        json={"target_client_type": "admin_web"},
        headers=auth_headers(
            user_id="CODEX-TEST-OPS",
            role_code="operations",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["message"] == "访问校验通过"


def test_supplier_can_login_miniprogram(auth_headers) -> None:
    response = client.post(
        "/api/v1/access/check",
        json={"target_client_type": "miniprogram"},
        headers=auth_headers(
            user_id="CODEX-TEST-SUPPLIER",
            role_code="supplier",
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["message"] == "访问校验通过"
