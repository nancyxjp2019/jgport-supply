from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_miniprogram_dev_login_returns_token_for_operator_role() -> None:
    response = client.post(
        "/api/v1/mini-auth/dev-login",
        json={"role_code": "operations"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["role_code"] == "operations"
    assert body["client_type"] == "miniprogram"
    assert body["miniprogram_allowed"] is True
    assert body["message"] == "小程序本地联调登录成功"


def test_miniprogram_dev_login_token_can_read_access_profile() -> None:
    login_response = client.post(
        "/api/v1/mini-auth/dev-login",
        json={"role_code": "finance"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/access/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    body = me_response.json()
    assert body["role_code"] == "finance"
    assert body["client_type"] == "miniprogram"
    assert body["miniprogram_allowed"] is True


def test_miniprogram_dev_login_customer_can_login_but_cannot_view_light_report() -> None:
    login_response = client.post(
        "/api/v1/mini-auth/dev-login",
        json={"role_code": "customer"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    report_response = client.get(
        "/api/v1/reports/light/overview",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert report_response.status_code == 403
    assert report_response.json()["detail"] == "当前角色无权访问该接口"


def test_bearer_token_with_invalid_signature_is_rejected() -> None:
    response = client.get(
        "/api/v1/access/me",
        headers={"Authorization": "Bearer m1.invalid.invalid"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "联调令牌签名校验失败"
