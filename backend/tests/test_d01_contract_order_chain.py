from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CUSTOMER_COMPANY_ID = "CODEX-TEST-CUSTOMER-COMPANY"
SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"


def test_d01_contract_reject_resubmit_then_order_finance_approve_chain(
    auth_headers,
) -> None:
    sales_contract_id = _create_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    _submit_contract(auth_headers, sales_contract_id, comment="D01 销售合同首次提审")

    reject_response = client.post(
        f"/api/v1/contracts/{sales_contract_id}/approve",
        json={"approval_result": False, "comment": "资料不完整，退回修改"},
        headers=auth_headers(),
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "草稿"

    updated_contract_no = f"CODEX-TEST-D01-SC-UPD-{uuid4().hex[:10]}"
    update_response = client.put(
        f"/api/v1/contracts/{sales_contract_id}",
        json={
            "contract_no": updated_contract_no,
            "customer_id": CUSTOMER_COMPANY_ID,
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 150, "unit_price": 6500.25},
                {"oil_product_id": "OIL-95", "qty_signed": 80, "unit_price": 6680.4},
            ],
        },
        headers=auth_headers(
            user_id=f"CODEX-TEST-D01-FINANCE-UPD-{uuid4().hex[:6]}",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "草稿"
    assert update_response.json()["contract_no"] == updated_contract_no

    _submit_contract(auth_headers, sales_contract_id, comment="D01 修改后再次提审")
    approve_response = client.post(
        f"/api/v1/contracts/{sales_contract_id}/approve",
        json={"approval_result": True, "comment": "D01 销售合同审批通过"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    approve_body = approve_response.json()
    assert approve_body["status"] == "生效中"
    assert approve_body["generated_task_count"] == 1

    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    sales_order_response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": 25.5,
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id=f"CODEX-TEST-D01-CUSTOMER-CREATE-{uuid4().hex[:6]}",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert sales_order_response.status_code == 200
    sales_order_id = sales_order_response.json()["id"]
    assert sales_order_response.json()["status"] == "草稿"

    submit_order_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/submit",
        json={"comment": "D01 客户提交订单审批"},
        headers=auth_headers(
            user_id=f"CODEX-TEST-D01-CUSTOMER-SUBMIT-{uuid4().hex[:6]}",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert submit_order_response.status_code == 200
    assert submit_order_response.json()["status"] == "待运营审批"

    ops_approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "D01 运营审批通过"},
        headers=auth_headers(
            user_id=f"CODEX-TEST-D01-OPS-{uuid4().hex[:6]}",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert ops_approve_response.status_code == 200
    assert ops_approve_response.json()["status"] == "待财务审批"

    finance_approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 16575.64,
            "actual_pay_amount": 16065.12,
            "comment": "D01 财务审批通过并生成采购订单",
        },
        headers=auth_headers(
            user_id=f"CODEX-TEST-D01-FINANCE-ORDER-{uuid4().hex[:6]}",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert finance_approve_response.status_code == 200
    finance_body = finance_approve_response.json()
    assert finance_body["status"] == "已衍生采购订单"
    assert finance_body["purchase_order_id"] is not None
    assert finance_body["generated_task_count"] == 2

    purchase_order_response = client.get(
        f"/api/v1/purchase-orders/{finance_body['purchase_order_id']}",
        headers=auth_headers(
            user_id=f"CODEX-TEST-D01-OPS-READ-{uuid4().hex[:6]}",
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


def _create_sales_contract(auth_headers, *, customer_id: str) -> int:
    response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-D01-SC-{uuid4().hex[:10]}",
            "customer_id": customer_id,
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 120, "unit_price": 6480.55}
            ],
        },
        headers=auth_headers(
            user_id=f"CODEX-TEST-D01-FINANCE-CREATE-{uuid4().hex[:6]}",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _submit_contract(auth_headers, contract_id: int, *, comment: str) -> None:
    response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": comment},
        headers=auth_headers(),
    )
    assert response.status_code == 200


def _create_effective_purchase_contract(auth_headers, *, supplier_id: str) -> int:
    create_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": f"CODEX-TEST-D01-PC-{uuid4().hex[:10]}",
            "supplier_id": supplier_id,
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 180, "unit_price": 6300.8}
            ],
        },
        headers=auth_headers(
            user_id=f"CODEX-TEST-D01-FINANCE-PC-{uuid4().hex[:6]}",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]

    _submit_contract(auth_headers, contract_id, comment="D01 采购合同提交")

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "D01 采购合同审批通过"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "生效中"
    return contract_id
