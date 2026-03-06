from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.mini_program_account import MiniProgramAccount
import app.services.wechat_login_service as wechat_login_service

client = TestClient(app)


def test_wechat_login_returns_binding_required_when_account_unbound(monkeypatch) -> None:
    monkeypatch.setattr(
        wechat_login_service,
        "exchange_wechat_code2session",
        lambda code: wechat_login_service.WeChatCode2SessionResult(
            openid="wx-openid-unbound-001",
            unionid="wx-unionid-unbound-001",
            session_key="session-key-001",
        ),
    )

    response = client.post("/api/v1/mini-auth/wechat-login", json={"code": "WX-CODE-001"})
    assert response.status_code == 200
    body = response.json()
    assert body["binding_required"] is True
    assert body["message"] == "当前微信账号未绑定业务角色，请联系管理员"
    assert body["debug_openid"] == "wx-openid-unbound-001"


def test_wechat_login_returns_token_when_account_is_bound(monkeypatch) -> None:
    monkeypatch.setattr(
        wechat_login_service,
        "exchange_wechat_code2session",
        lambda code: wechat_login_service.WeChatCode2SessionResult(
            openid="wx-openid-bound-001",
            unionid="wx-unionid-bound-001",
            session_key="session-key-002",
        ),
    )
    _upsert_mini_program_account(
        openid="wx-openid-bound-001",
        unionid=None,
        role_code="operations",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
    )

    response = client.post("/api/v1/mini-auth/wechat-login", json={"code": "WX-CODE-002"})
    assert response.status_code == 200
    body = response.json()
    assert body["binding_required"] is False
    assert body["role_code"] == "operations"
    assert body["client_type"] == "miniprogram"
    assert body["access_token"]

    me_response = client.get(
        "/api/v1/access/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["role_code"] == "operations"

    db = SessionLocal()
    try:
        account = db.scalar(select(MiniProgramAccount).where(MiniProgramAccount.openid == "wx-openid-bound-001"))
        assert account is not None
        assert account.unionid == "wx-unionid-bound-001"
        assert account.last_login_at is not None
    finally:
        db.close()


def test_wechat_login_blocks_binding_without_miniprogram_access(monkeypatch) -> None:
    monkeypatch.setattr(
        wechat_login_service,
        "exchange_wechat_code2session",
        lambda code: wechat_login_service.WeChatCode2SessionResult(
            openid="wx-openid-blocked-001",
            unionid=None,
            session_key="session-key-003",
        ),
    )
    _upsert_mini_program_account(
        openid="wx-openid-blocked-001",
        unionid=None,
        role_code="operations",
        company_id="CODEX-TEST-CUSTOMER-COMPANY",
        company_type="customer_company",
    )

    response = client.post("/api/v1/mini-auth/wechat-login", json={"code": "WX-CODE-003"})
    assert response.status_code == 403
    assert response.json()["detail"] == "当前微信账号未开放小程序访问"


def _upsert_mini_program_account(
    *,
    openid: str,
    unionid: str | None,
    role_code: str,
    company_id: str,
    company_type: str,
) -> None:
    db = SessionLocal()
    try:
        account = db.scalar(select(MiniProgramAccount).where(MiniProgramAccount.openid == openid))
        if account is None:
            account = MiniProgramAccount(
                openid=openid,
                unionid=unionid,
                role_code=role_code,
                company_id=company_id,
                company_type=company_type,
                display_name="AUTO-TEST-WX",
            )
            db.add(account)
        else:
            account.unionid = unionid
            account.role_code = role_code
            account.company_id = company_id
            account.company_type = company_type
            account.status = "生效"
            account.is_active = True
        db.commit()
    finally:
        db.close()
