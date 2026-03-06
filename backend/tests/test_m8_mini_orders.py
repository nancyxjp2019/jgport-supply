from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_customer_can_list_available_sales_contracts(auth_headers) -> None:
    customer_company_id = _build_company_id("CUSTOMER")
    other_customer_company_id = _build_company_id("OTHER")
    contract_id = _create_effective_sales_contract(auth_headers, customer_id=customer_company_id)
    other_contract_id = _create_effective_sales_contract(auth_headers, customer_id=other_customer_company_id)

    response = client.get(
        "/api/v1/sales-contracts/available",
        headers=auth_headers(
            user_id="CODEX-TEST-M8-CUSTOMER-CONTRACTS",
            role_code="customer",
            company_id=customer_company_id,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == contract_id
    assert body["items"][0]["customer_id"] == customer_company_id
    assert body["items"][0]["items"][0]["oil_product_id"] == "OIL-92"
    assert all(item["customer_id"] == customer_company_id for item in body["items"])
    assert all(item["id"] != other_contract_id for item in body["items"])


def test_customer_can_list_and_read_own_sales_orders(auth_headers) -> None:
    customer_company_id = _build_company_id("CUSTOMER")
    other_customer_company_id = _build_company_id("OTHER")
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=customer_company_id)
    other_contract_id = _create_effective_sales_contract(auth_headers, customer_id=other_customer_company_id)
    own_order_id = _create_sales_order_draft(auth_headers, sales_contract_id=sales_contract_id, company_id=customer_company_id)
    other_order_id = _create_sales_order_draft(auth_headers, sales_contract_id=other_contract_id, company_id=other_customer_company_id)

    list_response = client.get(
        "/api/v1/sales-orders?limit=50",
        headers=_customer_headers(auth_headers, customer_company_id, "CODEX-TEST-M8-CUSTOMER-LIST"),
    )
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == own_order_id
    assert body["items"][0]["sales_contract_no"].startswith("CODEX-TEST-M8-SALES-")
    assert all(item["id"] != other_order_id for item in body["items"])

    detail_response = client.get(
        f"/api/v1/sales-orders/{own_order_id}",
        headers=_customer_headers(auth_headers, customer_company_id, "CODEX-TEST-M8-CUSTOMER-DETAIL"),
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["id"] == own_order_id
    assert detail_body["sales_contract_no"].startswith("CODEX-TEST-M8-SALES-")


def test_customer_cannot_read_other_company_sales_order(auth_headers) -> None:
    customer_company_id = _build_company_id("CUSTOMER")
    other_customer_company_id = _build_company_id("OTHER")
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=other_customer_company_id)
    sales_order_id = _create_sales_order_draft(
        auth_headers,
        sales_contract_id=sales_contract_id,
        company_id=other_customer_company_id,
    )

    response = client.get(
        f"/api/v1/sales-orders/{sales_order_id}",
        headers=_customer_headers(auth_headers, customer_company_id, "CODEX-TEST-M8-CUSTOMER-BLOCK"),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前客户无权查看该销售订单"


def test_operator_admin_web_can_read_sales_order_list_and_detail(auth_headers) -> None:
    customer_company_id = _build_company_id("CUSTOMER")
    sales_contract_id = _create_effective_sales_contract(auth_headers, customer_id=customer_company_id)
    own_order_id = _create_sales_order_draft(auth_headers, sales_contract_id=sales_contract_id, company_id=customer_company_id)

    list_response = client.get(
        "/api/v1/sales-orders?limit=50",
        headers=auth_headers(
            user_id="CODEX-TEST-M8-OPS-READER",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert list_response.status_code == 200
    order_ids = {item["id"] for item in list_response.json()["items"]}
    assert own_order_id in order_ids

    detail_response = client.get(
        f"/api/v1/sales-orders/{own_order_id}",
        headers=auth_headers(
            user_id="CODEX-TEST-M8-OPS-DETAIL",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == own_order_id


def test_warehouse_cannot_query_customer_order_page_endpoints(auth_headers) -> None:
    response = client.get(
        "/api/v1/sales-contracts/available",
        headers=auth_headers(
            user_id="CODEX-TEST-M8-WAREHOUSE-BLOCK",
            role_code="warehouse",
            company_id="CODEX-TEST-WAREHOUSE-COMPANY",
            company_type="warehouse_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前身份无权查询可选销售合同"


def _customer_headers(auth_headers, company_id: str, user_id: str) -> dict[str, str]:
    return auth_headers(
        user_id=user_id,
        role_code="customer",
        company_id=company_id,
        company_type="customer_company",
        client_type="miniprogram",
    )


def _build_company_id(suffix: str) -> str:
    return f"CODEX-TEST-M8-{suffix}-{uuid4().hex[:8]}"


def _create_effective_sales_contract(auth_headers, *, customer_id: str) -> int:
    contract_no = f"CODEX-TEST-M8-SALES-{uuid4().hex[:10]}"
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": contract_no,
            "customer_id": customer_id,
            "items": [{"oil_product_id": "OIL-92", "qty_signed": 100, "unit_price": 6500.25}],
        },
        headers=auth_headers(
            user_id=f"CODEX-TEST-M8-FINANCE-CREATE-{uuid4().hex[:6]}",
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
        json={"comment": "M8订单页提交"},
        headers=auth_headers(
            user_id=f"CODEX-TEST-M8-FINANCE-SUBMIT-{uuid4().hex[:6]}",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M8订单页审批通过"},
        headers=auth_headers(
            user_id=f"CODEX-TEST-M8-FINANCE-APPROVE-{uuid4().hex[:6]}",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_sales_order_draft(auth_headers, *, sales_contract_id: int, company_id: str) -> int:
    response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": float(Decimal("10.000")),
            "unit_price": 6500.25,
        },
        headers=_customer_headers(auth_headers, company_id, f"CODEX-TEST-M8-CUSTOMER-CREATE-{uuid4().hex[:6]}"),
    )
    assert response.status_code == 200
    return response.json()["id"]
