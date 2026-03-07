from __future__ import annotations

from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app

client = TestClient(app)

SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"


def test_supplier_miniprogram_can_list_own_purchase_orders(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.get(
        "/api/v1/supplier/purchase-orders",
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-LIST",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["id"] == purchase_order_id for item in body["items"])
    matched = next(item for item in body["items"] if item["id"] == purchase_order_id)
    assert matched["supplier_id"] == SUPPLIER_COMPANY_ID
    assert matched["source_sales_order_no"]


def test_supplier_miniprogram_can_view_own_purchase_order_detail(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.get(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}",
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-DETAIL",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == purchase_order_id
    assert body["supplier_id"] == SUPPLIER_COMPANY_ID
    assert body["source_sales_order_no"]
    assert "downstream_tasks" not in body
    assert "idempotency_key" not in body


def test_supplier_cannot_read_other_supplier_purchase_order(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.get(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}",
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-OTHER",
            role_code="supplier",
            company_id="CODEX-TEST-SUPPLIER-OTHER-COMPANY",
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "当前供应商无权查看该采购订单"


def test_non_supplier_cannot_access_supplier_purchase_orders(auth_headers) -> None:
    _create_purchase_order(auth_headers, supplier_id=SUPPLIER_COMPANY_ID)

    response = client.get(
        "/api/v1/supplier/purchase-orders",
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-CUSTOMER-BLOCK",
            role_code="customer",
            company_id="CODEX-TEST-CUSTOMER-COMPANY",
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "当前角色无权访问该接口"


def _create_purchase_order(auth_headers, *, supplier_id: str) -> int:
    sales_contract_id = _create_effective_sales_contract(auth_headers)
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=supplier_id
    )
    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )
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
            user_id="CODEX-TEST-FINANCE-SUPPLIER-APPROVER",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200
    return int(response.json()["purchase_order_id"])


def _create_effective_sales_contract(auth_headers) -> int:
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-SALES-SUPPLIER-{uuid4().hex[:10]}",
            "customer_id": "CODEX-TEST-CUSTOMER-COMPANY",
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 100, "unit_price": 6500.25}
            ],
        },
        headers=auth_headers(),
    )
    contract_id = create_response.json()["id"]
    client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "提交审批"},
        headers=auth_headers(),
    )
    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "审批通过"},
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
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 100, "unit_price": 6200.12}
            ],
        },
        headers=auth_headers(),
    )
    contract_id = create_response.json()["id"]
    client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "提交审批"},
        headers=auth_headers(),
    )
    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "审批通过"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_sales_order_in_pending_finance(
    auth_headers, *, sales_contract_id: int
) -> int:
    create_response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": 12.345,
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-SUPPLIER-PO",
            role_code="customer",
            company_id="CODEX-TEST-CUSTOMER-COMPANY",
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    sales_order_id = create_response.json()["id"]
    client.post(
        f"/api/v1/sales-orders/{sales_order_id}/submit",
        json={"comment": "客户提交审批"},
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-SUPPLIER-SUBMIT",
            role_code="customer",
            company_id="CODEX-TEST-CUSTOMER-COMPANY",
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    ops_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "运营通过"},
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-SUPPLIER-PO",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert ops_response.status_code == 200
    return sales_order_id
