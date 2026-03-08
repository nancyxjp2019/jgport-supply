from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.business_audit_log import BusinessAuditLog

client = TestClient(app)


def test_finance_can_create_purchase_contract_draft(auth_headers) -> None:
    contract_no = f"CODEX-TEST-PC-{uuid4().hex[:10]}"
    response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": contract_no,
            "supplier_id": "CODEX-TEST-SUPPLIER-01",
            "items": [
                {
                    "oil_product_id": "OIL-92",
                    "qty_signed": 120.123,
                    "unit_price": 6350.18,
                },
                {
                    "oil_product_id": "OIL-95",
                    "qty_signed": 80.456,
                    "unit_price": 6450.56,
                },
            ],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE",
            role_code="finance",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contract_no"] == contract_no
    assert body["direction"] == "purchase"
    assert body["status"] == "草稿"
    assert body["supplier_id"] == "CODEX-TEST-SUPPLIER-01"
    assert body["threshold_release_snapshot"] is None
    assert len(body["items"]) == 2


def test_non_finance_or_admin_cannot_create_contract(auth_headers) -> None:
    response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-SC-{uuid4().hex[:10]}",
            "customer_id": "CODEX-TEST-CUSTOMER-01",
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 100, "unit_price": 6550.12}
            ],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-OPS",
            role_code="operations",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前角色无权访问该接口"


def test_contract_submit_transitions_draft_to_pending_approval(auth_headers) -> None:
    contract_id = _create_sales_contract(auth_headers)
    response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "提交审批测试"},
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE",
            role_code="finance",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "待审批"
    assert body["submit_comment"] == "提交审批测试"


def test_contract_draft_can_be_updated_after_reject_and_resubmitted(
    auth_headers,
) -> None:
    contract_id = _create_sales_contract(auth_headers)
    _submit_contract(contract_id, auth_headers)

    reject_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": False, "comment": "资料不完整，退回修改"},
        headers=auth_headers(),
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "草稿"

    updated_contract_no = f"CODEX-TEST-SC-UPD-{uuid4().hex[:10]}"
    update_response = client.put(
        f"/api/v1/contracts/{contract_id}",
        json={
            "contract_no": updated_contract_no,
            "customer_id": "CODEX-TEST-CUSTOMER-UPD",
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 120.5, "unit_price": 6200.2},
                {"oil_product_id": "OIL-95", "qty_signed": 66.6, "unit_price": 6500.8},
            ],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-UPD",
            role_code="finance",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert update_response.status_code == 200
    update_body = update_response.json()
    assert update_body["status"] == "草稿"
    assert update_body["contract_no"] == updated_contract_no
    assert update_body["customer_id"] == "CODEX-TEST-CUSTOMER-UPD"
    assert len(update_body["items"]) == 2
    assert update_body["approval_comment"] == "资料不完整，退回修改"

    update_audit_log = _get_contract_audit_log(
        contract_id=contract_id,
        event_code="M2-CONTRACT-UPDATE",
    )
    assert update_audit_log is not None
    assert update_audit_log.after_json["contract_no"] == updated_contract_no
    assert update_audit_log.extra_json["direction"] == "sales"

    resubmit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "修改后再次提审"},
        headers=auth_headers(),
    )
    assert resubmit_response.status_code == 200
    assert resubmit_response.json()["status"] == "待审批"
    assert resubmit_response.json()["submit_comment"] == "修改后再次提审"


def test_pending_approval_contract_cannot_be_updated(auth_headers) -> None:
    contract_id = _create_sales_contract(auth_headers)
    _submit_contract(contract_id, auth_headers)

    response = client.put(
        f"/api/v1/contracts/{contract_id}",
        json={
            "contract_no": f"CODEX-TEST-SC-UPD-{uuid4().hex[:10]}",
            "customer_id": "CODEX-TEST-CUSTOMER-PENDING",
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 100, "unit_price": 6200}
            ],
        },
        headers=auth_headers(),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "当前合同状态不允许修改"


def test_contract_update_duplicate_contract_no_is_blocked(auth_headers) -> None:
    existing_contract_no = f"CODEX-TEST-SC-EXIST-{uuid4().hex[:10]}"
    first_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": existing_contract_no,
            "customer_id": "CODEX-TEST-CUSTOMER-EXIST",
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 100, "unit_price": 6550.12}
            ],
        },
        headers=auth_headers(),
    )
    assert first_response.status_code == 200

    contract_id = _create_sales_contract(auth_headers)
    response = client.put(
        f"/api/v1/contracts/{contract_id}",
        json={
            "contract_no": existing_contract_no,
            "customer_id": "CODEX-TEST-CUSTOMER-UPD-DUP",
            "items": [
                {"oil_product_id": "OIL-95", "qty_signed": 99.9, "unit_price": 6500.23}
            ],
        },
        headers=auth_headers(),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "合同编号已存在"


@pytest.mark.parametrize(
    ("role_code", "company_type", "client_type", "expected_detail"),
    [
        ("operations", "operator_company", "admin_web", "当前角色无权访问该接口"),
        ("finance", "customer_company", "admin_web", "当前公司范围无权访问该接口"),
        ("finance", "operator_company", "miniprogram", "当前端类型无权访问该接口"),
    ],
)
def test_contract_update_blocks_unauthorized_actor(
    auth_headers,
    role_code: str,
    company_type: str,
    client_type: str,
    expected_detail: str,
) -> None:
    contract_id = _create_sales_contract(auth_headers)
    response = client.put(
        f"/api/v1/contracts/{contract_id}",
        json={
            "contract_no": f"CODEX-TEST-SC-UPD-{uuid4().hex[:10]}",
            "customer_id": "CODEX-TEST-CUSTOMER-AUTH",
            "items": [
                {"oil_product_id": "OIL-95", "qty_signed": 99.9, "unit_price": 6500.23}
            ],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-UNAUTHORIZED-UPD",
            role_code=role_code,
            company_type=company_type,
            client_type=client_type,
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == expected_detail


def test_purchase_contract_approval_writes_threshold_snapshots_and_effective_tasks(
    auth_headers,
) -> None:
    contract_id = _create_purchase_contract(auth_headers)
    _submit_contract(contract_id, auth_headers)

    thresholds_response = client.get(
        "/api/v1/system-configs/thresholds", headers=auth_headers()
    )
    assert thresholds_response.status_code == 200
    thresholds_body = thresholds_response.json()

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "审批通过"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    approve_body = approve_response.json()
    assert approve_body["status"] == "生效中"
    assert approve_body["generated_task_count"] == 2
    assert Decimal(str(approve_body["threshold_release_snapshot"])) == Decimal(
        str(thresholds_body["threshold_release"])
    )
    assert Decimal(str(approve_body["threshold_over_exec_snapshot"])) == Decimal(
        str(thresholds_body["threshold_over_exec"])
    )

    graph_response = client.get(
        f"/api/v1/contracts/{contract_id}/graph",
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-READ",
            role_code="operations",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert graph_response.status_code == 200
    graph_body = graph_response.json()
    assert len(graph_body["downstream_tasks"]) == 2
    assert {task["target_doc_type"] for task in graph_body["downstream_tasks"]} == {
        "payment_doc",
        "inbound_doc",
    }


def test_sales_contract_approval_creates_receipt_task(auth_headers) -> None:
    contract_id = _create_sales_contract(auth_headers)
    _submit_contract(contract_id, auth_headers)

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "销售合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    approve_body = approve_response.json()
    assert approve_body["status"] == "生效中"
    assert approve_body["generated_task_count"] == 1

    graph_response = client.get(
        f"/api/v1/contracts/{contract_id}/graph",
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-GRAPH",
            role_code="operations",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert graph_response.status_code == 200
    graph_body = graph_response.json()
    assert len(graph_body["downstream_tasks"]) == 1
    assert graph_body["downstream_tasks"][0]["target_doc_type"] == "receipt_doc"


def test_contract_reject_returns_to_draft_without_effective_tasks(auth_headers) -> None:
    contract_id = _create_sales_contract(auth_headers)
    _submit_contract(contract_id, auth_headers)

    reject_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": False, "comment": "资料不完整，退回修改"},
        headers=auth_headers(),
    )
    assert reject_response.status_code == 200
    reject_body = reject_response.json()
    assert reject_body["status"] == "草稿"
    assert reject_body["generated_task_count"] == 0
    assert reject_body["approval_comment"] == "资料不完整，退回修改"

    graph_response = client.get(
        f"/api/v1/contracts/{contract_id}/graph",
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-GRAPH-2",
            role_code="operations",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert graph_response.status_code == 200
    assert graph_response.json()["downstream_tasks"] == []


def test_duplicate_contract_no_and_duplicate_item_oil_product_are_blocked(
    auth_headers,
) -> None:
    contract_no = f"CODEX-TEST-UNIQUE-{uuid4().hex[:10]}"
    first_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": contract_no,
            "supplier_id": "CODEX-TEST-SUPPLIER-DUP",
            "items": [
                {"oil_product_id": "OIL-0", "qty_signed": 100, "unit_price": 6000}
            ],
        },
        headers=auth_headers(),
    )
    assert first_response.status_code == 200

    duplicate_contract_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": contract_no,
            "supplier_id": "CODEX-TEST-SUPPLIER-DUP",
            "items": [
                {"oil_product_id": "OIL-1", "qty_signed": 100, "unit_price": 6000}
            ],
        },
        headers=auth_headers(),
    )
    assert duplicate_contract_response.status_code == 409
    assert duplicate_contract_response.json()["detail"] == "合同编号已存在"

    duplicate_item_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-DUPITEM-{uuid4().hex[:10]}",
            "customer_id": "CODEX-TEST-CUSTOMER-DUP",
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 100, "unit_price": 6200},
                {"oil_product_id": "OIL-92", "qty_signed": 200, "unit_price": 6300},
            ],
        },
        headers=auth_headers(),
    )
    assert duplicate_item_response.status_code == 422
    assert duplicate_item_response.json()["message"] == "请求参数校验失败"
    assert (
        duplicate_item_response.json()["detail"][0]["msg"]
        == "同一合同下油品明细不能重复"
    )


def _create_purchase_contract(auth_headers) -> int:
    response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": f"CODEX-TEST-PC-{uuid4().hex[:10]}",
            "supplier_id": "CODEX-TEST-SUPPLIER-AUTO",
            "items": [
                {
                    "oil_product_id": "OIL-92",
                    "qty_signed": 120.123,
                    "unit_price": 6350.18,
                }
            ],
        },
        headers=auth_headers(),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_sales_contract(auth_headers) -> int:
    response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-SC-{uuid4().hex[:10]}",
            "customer_id": "CODEX-TEST-CUSTOMER-AUTO",
            "items": [
                {
                    "oil_product_id": "OIL-95",
                    "qty_signed": 99.999,
                    "unit_price": 6500.23,
                }
            ],
        },
        headers=auth_headers(),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _submit_contract(contract_id: int, auth_headers) -> None:
    response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "自动化测试提审"},
        headers=auth_headers(),
    )
    assert response.status_code == 200


def _get_contract_audit_log(
    *, contract_id: int, event_code: str
) -> BusinessAuditLog | None:
    db = SessionLocal()
    try:
        return db.scalar(
            select(BusinessAuditLog).where(
                BusinessAuditLog.biz_type == "contract",
                BusinessAuditLog.biz_id == f"contract:{contract_id}",
                BusinessAuditLog.event_code == event_code,
            )
        )
    finally:
        db.close()
