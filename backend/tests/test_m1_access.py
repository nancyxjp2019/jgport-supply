from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_customer_cannot_login_admin_web() -> None:
    response = client.post(
        "/api/v1/access/check",
        json={
            "role_code": "customer",
            "company_type": "customer_company",
            "client_type": "admin_web",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前角色不允许登录该端"


def test_operations_can_login_admin_web() -> None:
    response = client.post(
        "/api/v1/access/check",
        json={
            "role_code": "operations",
            "company_type": "operator_company",
            "client_type": "admin_web",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["message"] == "访问校验通过"


def test_supplier_can_login_miniprogram() -> None:
    response = client.post(
        "/api/v1/access/check",
        json={
            "role_code": "supplier",
            "company_type": "supplier_company",
            "client_type": "miniprogram",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["message"] == "访问校验通过"
