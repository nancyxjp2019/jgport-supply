from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.business_audit_log import BusinessAuditLog
from app.models.company_profile import CompanyProfile

client = TestClient(app)


def test_company_routes_require_admin_identity(auth_headers) -> None:
    response = client.get(
        "/api/v1/companies",
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-COMPANY",
            role_code="finance",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前角色无权访问该接口"


def test_create_operator_and_child_company_and_query_detail(auth_headers) -> None:
    headers = auth_headers(user_id="CODEX-TEST-ADMIN-COMPANY")

    create_operator_response = client.post(
        "/api/v1/companies",
        json={
            "company_id": "AUTO-TEST-OPERATOR-G1-001",
            "company_name": "AUTO-TEST-运营商一号",
            "company_type": "operator_company",
            "remark": "AUTO-TEST-根公司",
        },
        headers=headers,
    )
    assert create_operator_response.status_code == 201
    operator_body = create_operator_response.json()
    assert operator_body["company_id"] == "AUTO-TEST-OPERATOR-G1-001"
    assert operator_body["status"] == "启用"
    assert operator_body["message"] == "公司创建成功"

    create_customer_response = client.post(
        "/api/v1/companies",
        json={
            "company_id": "AUTO-TEST-CUSTOMER-G1-001",
            "company_name": "AUTO-TEST-客户一号",
            "company_type": "customer_company",
            "parent_company_id": "AUTO-TEST-OPERATOR-G1-001",
            "remark": "AUTO-TEST-客户挂靠运营商",
        },
        headers=headers,
    )
    assert create_customer_response.status_code == 201
    customer_body = create_customer_response.json()
    assert customer_body["parent_company_id"] == "AUTO-TEST-OPERATOR-G1-001"
    assert customer_body["parent_company_name"] == "AUTO-TEST-运营商一号"

    list_response = client.get(
        "/api/v1/companies",
        params={"company_type": "customer_company"},
        headers=headers,
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    assert any(
        item["company_id"] == "AUTO-TEST-CUSTOMER-G1-001" for item in list_body["items"]
    )

    detail_response = client.get(
        "/api/v1/companies/AUTO-TEST-OPERATOR-G1-001", headers=headers
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["child_company_count"] == 1
    assert detail_body["message"] == "查询成功"


def test_non_operator_company_requires_enabled_operator_parent(auth_headers) -> None:
    headers = auth_headers(user_id="CODEX-TEST-ADMIN-COMPANY-02")
    response = client.post(
        "/api/v1/companies",
        json={
            "company_id": "AUTO-TEST-SUPPLIER-G1-001",
            "company_name": "AUTO-TEST-供应商一号",
            "company_type": "supplier_company",
            "remark": "AUTO-TEST-缺少归属运营商",
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "非运营商公司必须绑定归属运营商"


def test_disable_company_blocks_when_enabled_children_exist(auth_headers) -> None:
    headers = auth_headers(user_id="CODEX-TEST-ADMIN-COMPANY-03")
    client.post(
        "/api/v1/companies",
        json={
            "company_id": "AUTO-TEST-OPERATOR-G1-002",
            "company_name": "AUTO-TEST-运营商二号",
            "company_type": "operator_company",
        },
        headers=headers,
    )
    client.post(
        "/api/v1/companies",
        json={
            "company_id": "AUTO-TEST-WAREHOUSE-G1-001",
            "company_name": "AUTO-TEST-仓库一号",
            "company_type": "warehouse_company",
            "parent_company_id": "AUTO-TEST-OPERATOR-G1-002",
        },
        headers=headers,
    )

    block_response = client.post(
        "/api/v1/companies/AUTO-TEST-OPERATOR-G1-002/status",
        json={"enabled": False, "reason": "AUTO-TEST-尝试停用上级"},
        headers=headers,
    )
    assert block_response.status_code == 409
    assert block_response.json()["detail"] == "当前公司仍存在启用中的下级公司，禁止停用"

    disable_child_response = client.post(
        "/api/v1/companies/AUTO-TEST-WAREHOUSE-G1-001/status",
        json={"enabled": False, "reason": "AUTO-TEST-先停用下级"},
        headers=headers,
    )
    assert disable_child_response.status_code == 200
    assert disable_child_response.json()["status"] == "停用"

    disable_parent_response = client.post(
        "/api/v1/companies/AUTO-TEST-OPERATOR-G1-002/status",
        json={"enabled": False, "reason": "AUTO-TEST-停用上级"},
        headers=headers,
    )
    assert disable_parent_response.status_code == 200
    assert disable_parent_response.json()["status"] == "停用"


def test_update_company_writes_audit_log(auth_headers) -> None:
    headers = auth_headers(user_id="CODEX-TEST-ADMIN-COMPANY-04")
    client.post(
        "/api/v1/companies",
        json={
            "company_id": "AUTO-TEST-OPERATOR-G1-003",
            "company_name": "AUTO-TEST-运营商三号",
            "company_type": "operator_company",
        },
        headers=headers,
    )

    update_response = client.put(
        "/api/v1/companies/AUTO-TEST-OPERATOR-G1-003",
        json={
            "company_name": "AUTO-TEST-运营商三号-更新",
            "remark": "AUTO-TEST-更新备注",
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["company_name"] == "AUTO-TEST-运营商三号-更新"

    db = SessionLocal()
    try:
        company = db.get(CompanyProfile, "AUTO-TEST-OPERATOR-G1-003")
        assert company is not None
        assert company.company_name == "AUTO-TEST-运营商三号-更新"

        logs = list(
            db.scalars(
                select(BusinessAuditLog)
                .where(BusinessAuditLog.biz_type == "company_profile")
                .where(BusinessAuditLog.biz_id == "AUTO-TEST-OPERATOR-G1-003")
                .order_by(BusinessAuditLog.id.asc())
            ).all()
        )
        assert [log.event_code for log in logs] == [
            "G1-COMPANY-CREATE",
            "G1-COMPANY-UPDATE",
        ]
    finally:
        db.close()
