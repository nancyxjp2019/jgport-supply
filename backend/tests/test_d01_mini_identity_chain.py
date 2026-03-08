from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests import test_m7_reports as report_helpers
from tests import test_m8_wechat_auth as wechat_helpers

client = TestClient(app)


def test_d01_mini_identity_chain_dev_login_refresh_and_light_report() -> None:
    artifact_baseline = _capture_report_artifact_baseline()
    try:
        login_response = client.post(
            "/api/v1/mini-auth/dev-login",
            json={"role_code": "operations"},
        )
        assert login_response.status_code == 200
        login_body = login_response.json()
        assert login_body["client_type"] == "miniprogram"
        assert login_body["role_code"] == "operations"

        me_response = client.get(
            "/api/v1/access/me",
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["role_code"] == "operations"

        refresh_response = client.post(
            "/api/v1/access/session/refresh",
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        )
        assert refresh_response.status_code == 200
        refresh_body = refresh_response.json()
        assert refresh_body["message"] == "会话续期成功"
        assert refresh_body["role_code"] == "operations"

        report_response = client.get(
            "/api/v1/reports/light/overview",
            headers={"Authorization": f"Bearer {refresh_body['access_token']}"},
        )
        assert report_response.status_code == 200
        report_body = report_response.json()
        assert report_body["metric_version"] == "v1"
        assert report_body["message"] == "轻量报表查询成功"
        assert "abnormal_count" in report_body

        blocked_login_response = client.post(
            "/api/v1/mini-auth/dev-login",
            json={"role_code": "customer"},
        )
        assert blocked_login_response.status_code == 200
        blocked_report_response = client.get(
            "/api/v1/reports/light/overview",
            headers={
                "Authorization": f"Bearer {blocked_login_response.json()['access_token']}"
            },
        )
        assert blocked_report_response.status_code == 403
        assert blocked_report_response.json()["detail"] == "当前角色无权访问该接口"
    finally:
        _cleanup_report_artifacts(artifact_baseline)


def test_d01_mini_identity_chain_wechat_login_binding_refresh_and_light_report(
    monkeypatch,
) -> None:
    artifact_baseline = _capture_report_artifact_baseline()
    try:
        monkeypatch.setattr(
            wechat_helpers.wechat_login_service,
            "exchange_wechat_code2session",
            lambda code: wechat_helpers.wechat_login_service.WeChatCode2SessionResult(
                openid="wx-openid-d01-unbound",
                unionid="wx-unionid-d01-unbound",
                session_key="session-key-d01-unbound",
            ),
        )
        unbound_response = client.post(
            "/api/v1/mini-auth/wechat-login",
            json={"code": "WX-D01-UNBOUND"},
        )
        assert unbound_response.status_code == 200
        assert unbound_response.json()["binding_required"] is True

        wechat_helpers._upsert_mini_program_account(
            openid="wx-openid-d01-bound",
            unionid=None,
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
        )
        monkeypatch.setattr(
            wechat_helpers.wechat_login_service,
            "exchange_wechat_code2session",
            lambda code: wechat_helpers.wechat_login_service.WeChatCode2SessionResult(
                openid="wx-openid-d01-bound",
                unionid="wx-unionid-d01-bound",
                session_key="session-key-d01-bound",
            ),
        )

        bound_response = client.post(
            "/api/v1/mini-auth/wechat-login",
            json={"code": "WX-D01-BOUND"},
        )
        assert bound_response.status_code == 200
        bound_body = bound_response.json()
        assert bound_body["binding_required"] is False
        assert bound_body["role_code"] == "finance"

        refresh_response = client.post(
            "/api/v1/access/session/refresh",
            headers={"Authorization": f"Bearer {bound_body['access_token']}"},
        )
        assert refresh_response.status_code == 200
        refreshed_token = refresh_response.json()["access_token"]

        report_response = client.get(
            "/api/v1/reports/light/overview",
            headers={"Authorization": f"Bearer {refreshed_token}"},
        )
        assert report_response.status_code == 200
        assert report_response.json()["message"] == "轻量报表查询成功"
    finally:
        _cleanup_report_artifacts(artifact_baseline)


def _capture_report_artifact_baseline() -> dict[str, set[int]]:
    db = report_helpers.SessionLocal()
    try:
        return {
            "snapshot_ids": {
                int(row.id)
                for row in db.scalars(
                    report_helpers.select(report_helpers.ReportSnapshot)
                ).all()
            },
            "audit_log_ids": {
                int(row.id)
                for row in db.scalars(
                    report_helpers.select(report_helpers.BusinessAuditLog).where(
                        report_helpers.BusinessAuditLog.biz_type.in_(
                            [
                                "report_daily_contract_scan",
                                "report_daily_contract_scan_state",
                            ]
                        )
                    )
                ).all()
            },
        }
    finally:
        db.close()


def _cleanup_report_artifacts(artifact_baseline: dict[str, set[int]]) -> None:
    db = report_helpers.SessionLocal()
    try:
        for row in db.scalars(
            report_helpers.select(report_helpers.ReportSnapshot)
        ).all():
            if int(row.id) not in artifact_baseline["snapshot_ids"]:
                db.delete(row)
        for row in db.scalars(
            report_helpers.select(report_helpers.BusinessAuditLog).where(
                report_helpers.BusinessAuditLog.biz_type.in_(
                    [
                        "report_daily_contract_scan",
                        "report_daily_contract_scan_state",
                    ]
                )
            )
        ).all():
            if int(row.id) not in artifact_baseline["audit_log_ids"]:
                db.delete(row)
        db.commit()
    finally:
        db.close()
