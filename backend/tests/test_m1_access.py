from fastapi.testclient import TestClient

from app.core.auth_actor import AuthenticatedActor
from app.core.direct_auth_token import issue_direct_auth_token
from app.main import app

client = TestClient(app)


def test_access_check_requires_authenticated_identity() -> None:
    response = client.post(
        "/api/v1/access/check",
        json={"target_client_type": "admin_web"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "未认证身份，禁止访问"


def test_access_me_returns_current_actor_and_permissions(auth_headers) -> None:
    response = client.get(
        "/api/v1/access/me",
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE",
            role_code="finance",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "CODEX-TEST-FINANCE"
    assert body["role_code"] == "finance"
    assert body["admin_web_allowed"] is True
    assert body["miniprogram_allowed"] is True
    assert body["message"] == "身份读取成功"


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


def test_access_session_refresh_requires_bearer_token(auth_headers) -> None:
    response = client.post(
        "/api/v1/access/session/refresh",
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-REFRESH-PROXY",
            role_code="operations",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "会话续期仅支持登录令牌"


def test_access_session_refresh_returns_new_token_and_profile() -> None:
    login_response = client.post(
        "/api/v1/mini-auth/dev-login",
        json={"role_code": "operations"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    refresh_response = client.post(
        "/api/v1/access/session/refresh",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in_seconds"] == 7200
    assert body["role_code"] == "operations"
    assert body["client_type"] == "miniprogram"
    assert body["miniprogram_allowed"] is True
    assert body["message"] == "会话续期成功"

    me_response = client.get(
        "/api/v1/access/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["role_code"] == "operations"


def test_access_session_refresh_accepts_recently_expired_token() -> None:
    expired_token = issue_direct_auth_token(
        AuthenticatedActor(
            user_id="AUTO-TEST-MINI-OPS-001",
            role_code="operations",
            company_id="AUTO-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="miniprogram",
        ),
        expires_in_seconds=-60,
    )

    refresh_response = client.post(
        "/api/v1/access/session/refresh",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["token_type"] == "Bearer"
    assert body["message"] == "会话续期成功"


def test_access_session_refresh_rejects_token_out_of_refresh_window() -> None:
    stale_token = issue_direct_auth_token(
        AuthenticatedActor(
            user_id="AUTO-TEST-MINI-OPS-001",
            role_code="operations",
            company_id="AUTO-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="miniprogram",
        ),
        expires_in_seconds=-86500,
    )

    refresh_response = client.post(
        "/api/v1/access/session/refresh",
        headers={"Authorization": f"Bearer {stale_token}"},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "登录令牌已过续期窗口，请重新登录"
