from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CUSTOMER_COMPANY_ID = "CODEX-TEST-CUSTOMER-COMPANY"
SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"


def test_customer_miniprogram_can_create_sales_order_draft(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": 12.345,
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-USER",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "草稿"
    assert body["sales_contract_id"] == sales_contract_id
    assert body["oil_product_id"] == "OIL-92"
    assert Decimal(str(body["unit_price"])) == Decimal("6500.25")


def test_invalid_role_cannot_create_sales_order(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": 10,
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-WAREHOUSE-USER",
            role_code="warehouse",
            company_id="CODEX-TEST-WAREHOUSE-COMPANY",
            company_type="warehouse_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前身份无权操作销售订单"


def test_create_sales_order_requires_effective_sales_contract_and_matching_oil_product(auth_headers) -> None:
    draft_contract_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-SALES-DRAFT-{uuid4().hex[:10]}",
            "customer_id": CUSTOMER_COMPANY_ID,
            "items": [{"oil_product_id": "OIL-92", "qty_signed": 100, "unit_price": 6500.25}],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-DRAFT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert draft_contract_response.status_code == 200
    draft_contract_id = draft_contract_response.json()["id"]

    draft_response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": draft_contract_id,
            "oil_product_id": "OIL-92",
            "qty": 10,
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-USER-DRAFT",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert draft_response.status_code == 409
    assert draft_response.json()["detail"] == "销售合同未生效，禁止创建销售订单"

    effective_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    invalid_oil_response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": effective_contract_id,
            "oil_product_id": "OIL-95",
            "qty": 10,
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-USER-OIL",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert invalid_oil_response.status_code == 409
    assert invalid_oil_response.json()["detail"] == "合同未包含当前油品明细"


def test_sales_order_submit_requires_same_customer_company(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    sales_order_id = _create_sales_order_draft(auth_headers, sales_contract_id=sales_contract_id)

    response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/submit",
        json={"comment": "客户提交审批"},
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-OTHER",
            role_code="customer",
            company_id="CODEX-TEST-OTHER-CUSTOMER-COMPANY",
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前客户无权提交该销售订单"


def test_sales_order_submit_and_ops_approve_flow(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    sales_order_id = _create_sales_order_draft(auth_headers, sales_contract_id=sales_contract_id)

    submit_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/submit",
        json={"comment": "客户提交审批"},
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-SUBMIT",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "待运营审批"

    ops_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "运营通过"},
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-APPROVER",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert ops_response.status_code == 200
    assert ops_response.json()["status"] == "待财务审批"


def test_ops_reject_returns_sales_order_to_draft(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    sales_order_id = _create_sales_order_in_pending_ops(auth_headers, sales_contract_id=sales_contract_id)
    response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": False, "comment": "资料不全"},
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-REJECT",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "草稿"


def test_finance_approve_generates_purchase_order_and_derivative_tasks(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    purchase_contract_id = _create_effective_purchase_contract(auth_headers, supplier_id=SUPPLIER_COMPANY_ID)
    sales_order_id = _create_sales_order_in_pending_finance(auth_headers, sales_contract_id=sales_contract_id)

    response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 12000.34,
            "actual_pay_amount": 11800.12,
            "comment": "财务通过",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-APPROVER",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "已衍生采购订单"
    assert body["purchase_order_id"] is not None
    assert body["generated_task_count"] == 2

    purchase_order_response = client.get(
        f"/api/v1/purchase-orders/{body['purchase_order_id']}",
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-ORDER-READ",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert purchase_order_response.status_code == 200
    purchase_order_body = purchase_order_response.json()
    assert purchase_order_body["purchase_contract_id"] == purchase_contract_id
    assert purchase_order_body["source_sales_order_id"] == sales_order_id
    assert purchase_order_body["zero_pay_exception_flag"] is False
    assert len(purchase_order_body["downstream_tasks"]) == 2
    assert {task["target_doc_type"] for task in purchase_order_body["downstream_tasks"]} == {
        "receipt_doc",
        "payment_doc",
    }

    audit_response = client.get(
        f"/api/v1/audit/logs?biz_id=purchase_order:{body['purchase_order_id']}",
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-AUDIT-READ",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert audit_response.status_code == 200
    audit_items = audit_response.json()["items"]
    assert len(audit_items) == 1
    assert audit_items[0]["event_code"] == "M3-PURCHASE-ORDER-CREATE"


def test_finance_approve_requires_valid_purchase_contract(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    sales_order_id = _create_sales_order_in_pending_finance(auth_headers, sales_contract_id=sales_contract_id)

    response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": sales_contract_id,
            "actual_receipt_amount": 10000,
            "actual_pay_amount": 9800,
            "comment": "财务通过",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-INVALID-PC",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "当前合同不是采购合同，禁止绑定采购订单"


def test_finance_reject_sets_sales_order_rejected(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    sales_order_id = _create_sales_order_in_pending_finance(auth_headers, sales_contract_id=sales_contract_id)

    response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": False,
            "comment": "回款资料不足",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-REJECT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "驳回"
    assert body["purchase_order_id"] is None
    assert body["generated_task_count"] == 0


def test_rejected_sales_order_update_returns_to_draft(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    sales_order_id = _create_sales_order_in_pending_finance(auth_headers, sales_contract_id=sales_contract_id)

    reject_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": False,
            "comment": "先驳回再修改",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-REJECT-TO-DRAFT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "驳回"

    update_response = client.put(
        f"/api/v1/sales-orders/{sales_order_id}",
        json={
            "oil_product_id": "OIL-92",
            "qty": 15.678,
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-UPDATE-REJECTED",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert update_response.status_code == 200
    update_body = update_response.json()
    assert update_body["status"] == "草稿"
    assert Decimal(str(update_body["qty_ordered"])) == Decimal("15.678")


def test_zero_pay_exception_still_binds_purchase_contract(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=CUSTOMER_COMPANY_ID)
    purchase_contract_id = _create_effective_purchase_contract(auth_headers, supplier_id=SUPPLIER_COMPANY_ID)
    sales_order_id = _create_sales_order_in_pending_finance(auth_headers, sales_contract_id=sales_contract_id)

    response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 10000,
            "actual_pay_amount": 0,
            "comment": "0付款例外",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-ZERO-PAY",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    purchase_order_id = response.json()["purchase_order_id"]

    detail_response = client.get(
        f"/api/v1/purchase-orders/{purchase_order_id}",
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-ZERO-PAY",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["purchase_contract_id"] == purchase_contract_id
    assert detail_body["zero_pay_exception_flag"] is True
    assert len(detail_body["downstream_tasks"]) == 2


def _create_effective_sales_contract(auth_headers, *, customer_id: str) -> int:
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-SALES-{uuid4().hex[:10]}",
            "customer_id": customer_id,
            "items": [{"oil_product_id": "OIL-92", "qty_signed": 300, "unit_price": 6500.25}],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-CREATE-SALES-CONTRACT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "销售合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "销售合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_effective_purchase_contract(auth_headers, *, supplier_id: str) -> int:
    create_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": f"CODEX-TEST-PURCHASE-{uuid4().hex[:10]}",
            "supplier_id": supplier_id,
            "items": [{"oil_product_id": "OIL-92", "qty_signed": 400, "unit_price": 6300.80}],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-CREATE-PURCHASE-CONTRACT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "采购合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "采购合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_sales_order_draft(auth_headers, *, sales_contract_id: int) -> int:
    response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": 12.345,
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-CREATE-ORDER",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_sales_order_in_pending_ops(auth_headers, *, sales_contract_id: int) -> int:
    sales_order_id = _create_sales_order_draft(auth_headers, sales_contract_id=sales_contract_id)
    response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/submit",
        json={"comment": "自动化提交审批"},
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-SUBMIT-ORDER",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 200
    return sales_order_id


def _create_sales_order_in_pending_finance(auth_headers, *, sales_contract_id: int) -> int:
    sales_order_id = _create_sales_order_in_pending_ops(auth_headers, sales_contract_id=sales_contract_id)
    response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "自动化运营审批通过"},
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-AUTO",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    return sales_order_id
