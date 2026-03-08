from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.contract import Contract
from app.models.contract_item import ContractItem
from app.models.inbound_doc import InboundDoc

client = TestClient(app)

CUSTOMER_COMPANY_ID = "CODEX-TEST-CUSTOMER-COMPANY"
SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"


def test_d01_inventory_chain_inbound_outbound_validation_and_qty_accumulation(
    auth_headers,
) -> None:
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        qty_signed=Decimal("100.000"),
    )
    sales_contract_id = _create_effective_sales_contract(
        auth_headers,
        customer_id=CUSTOMER_COMPANY_ID,
        qty_signed=Decimal("100.000"),
    )
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
    )

    inbound_doc = _query_inbound_docs(contract_id=purchase_contract_id)[0]
    inbound_submit_response = client.post(
        f"/api/v1/inbound-docs/{inbound_doc.id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-D01-INV-INBOUND-SUBMIT"),
    )
    assert inbound_submit_response.status_code == 200
    assert inbound_submit_response.json()["status"] == "已过账"

    contract_item_after_inbound = _query_contract_item(
        contract_id=purchase_contract_id,
        oil_product_id="OIL-92",
    )
    assert contract_item_after_inbound is not None
    assert contract_item_after_inbound.qty_in_acc == Decimal("100.000")

    first_outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-D01-INV-SYS-001",
        actual_qty=Decimal("60.000"),
    )
    first_outbound_submit_response = client.post(
        f"/api/v1/outbound-docs/{first_outbound_doc_id}/submit",
        json={"actual_qty": 60, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(
            auth_headers, "CODEX-TEST-D01-INV-OUTBOUND-SUBMIT-1"
        ),
    )
    assert first_outbound_submit_response.status_code == 200
    assert first_outbound_submit_response.json()["status"] == "已过账"

    failed_outbound_doc_id = _create_manual_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        oil_product_id="OIL-92",
        manual_ref_no="CODEX-TEST-D01-INV-MANUAL-001",
        actual_qty=Decimal("46.000"),
    )
    failed_outbound_submit_response = client.post(
        f"/api/v1/outbound-docs/{failed_outbound_doc_id}/submit",
        json={"actual_qty": 46, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-D01-INV-OUTBOUND-BLOCK"),
    )
    assert failed_outbound_submit_response.status_code == 200
    assert failed_outbound_submit_response.json()["status"] == "校验失败"

    contract_item_after_failed_submit = _query_contract_item(
        contract_id=sales_contract_id,
        oil_product_id="OIL-92",
    )
    assert contract_item_after_failed_submit is not None
    assert contract_item_after_failed_submit.qty_out_acc == Decimal("60.000")

    second_outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-D01-INV-SYS-002",
        actual_qty=Decimal("40.000"),
    )
    second_outbound_submit_response = client.post(
        f"/api/v1/outbound-docs/{second_outbound_doc_id}/submit",
        json={"actual_qty": 40, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(
            auth_headers, "CODEX-TEST-D01-INV-OUTBOUND-SUBMIT-2"
        ),
    )
    assert second_outbound_submit_response.status_code == 200
    assert second_outbound_submit_response.json()["status"] == "已过账"

    sales_contract = _query_contract(sales_contract_id)
    assert sales_contract is not None
    assert sales_contract.status == "数量履约完成"

    contract_item_after_second_submit = _query_contract_item(
        contract_id=sales_contract_id,
        oil_product_id="OIL-92",
    )
    assert contract_item_after_second_submit is not None
    assert contract_item_after_second_submit.qty_out_acc == Decimal("100.000")


def test_d01_inventory_chain_unauthorized_identity_boundary_for_execution_actions(
    auth_headers,
) -> None:
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        qty_signed=Decimal("50.000"),
    )
    inbound_doc = _query_inbound_docs(contract_id=purchase_contract_id)[0]

    inbound_submit_response = client.post(
        f"/api/v1/inbound-docs/{inbound_doc.id}/submit",
        json={"actual_qty": 50, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_customer_headers(auth_headers, "CODEX-TEST-D01-INV-CUSTOMER-INBOUND"),
    )
    assert inbound_submit_response.status_code == 403
    assert inbound_submit_response.json()["detail"] == "当前身份无权操作出入库单"

    sales_contract_id = _create_effective_sales_contract(
        auth_headers,
        customer_id=CUSTOMER_COMPANY_ID,
        qty_signed=Decimal("50.000"),
    )
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("50.000"),
    )

    warehouse_confirm_response = client.post(
        "/api/v1/outbound-docs/warehouse-confirm",
        json={
            "contract_id": sales_contract_id,
            "sales_order_id": sales_order_id,
            "source_ticket_no": "CODEX-TEST-D01-INV-OPS-SYS-001",
            "actual_qty": 20,
            "warehouse_id": "CODEX-TEST-WH-001",
        },
        headers=_customer_headers(auth_headers, "CODEX-TEST-D01-INV-CUSTOMER-OUTBOUND"),
    )
    assert warehouse_confirm_response.status_code == 403
    assert warehouse_confirm_response.json()["detail"] == "当前身份无权操作出入库单"


def _query_inbound_docs(*, contract_id: int) -> list[InboundDoc]:
    with SessionLocal() as db:
        statement = (
            select(InboundDoc)
            .where(InboundDoc.contract_id == contract_id)
            .order_by(InboundDoc.id)
        )
        return list(db.scalars(statement).all())


def _query_contract(contract_id: int) -> Contract | None:
    with SessionLocal() as db:
        return db.get(Contract, contract_id)


def _query_contract_item(
    *, contract_id: int, oil_product_id: str
) -> ContractItem | None:
    with SessionLocal() as db:
        statement = select(ContractItem).where(
            ContractItem.contract_id == contract_id,
            ContractItem.oil_product_id == oil_product_id,
        )
        return db.scalar(statement)


def _create_effective_purchase_contract(
    auth_headers,
    *,
    supplier_id: str,
    qty_signed: Decimal,
) -> int:
    create_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": f"CODEX-TEST-D01-INV-PC-{uuid4().hex[:10]}",
            "supplier_id": supplier_id,
            "items": [
                {
                    "oil_product_id": "OIL-92",
                    "qty_signed": float(qty_signed),
                    "unit_price": 6300.80,
                }
            ],
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-INV-PC-CREATE"),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "D01 仓储采购合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "D01 仓储采购合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_effective_sales_contract(
    auth_headers,
    *,
    customer_id: str,
    qty_signed: Decimal,
) -> int:
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-D01-INV-SC-{uuid4().hex[:10]}",
            "customer_id": customer_id,
            "items": [
                {
                    "oil_product_id": "OIL-92",
                    "qty_signed": float(qty_signed),
                    "unit_price": 6500.25,
                }
            ],
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-INV-SC-CREATE"),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "D01 仓储销售合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "D01 仓储销售合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_sales_order_derived(
    auth_headers,
    *,
    sales_contract_id: int,
    purchase_contract_id: int,
    qty: Decimal,
) -> int:
    create_response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": float(qty),
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-D01-INV-CUSTOMER-CREATE",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert create_response.status_code == 200
    sales_order_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/submit",
        json={"comment": "D01 仓储主链客户提交订单"},
        headers=auth_headers(
            user_id="CODEX-TEST-D01-INV-CUSTOMER-SUBMIT",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert submit_response.status_code == 200

    ops_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "D01 仓储主链运营审批通过"},
        headers=_operations_headers(auth_headers, "CODEX-TEST-D01-INV-OPS-APPROVE"),
    )
    assert ops_response.status_code == 200

    finance_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 12000.34,
            "actual_pay_amount": 11800.12,
            "comment": "D01 仓储主链财务审批通过",
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-INV-FINANCE-APPROVE"),
    )
    assert finance_response.status_code == 200
    return sales_order_id


def _create_system_outbound_doc(
    auth_headers,
    *,
    contract_id: int,
    sales_order_id: int,
    source_ticket_no: str,
    actual_qty: Decimal,
) -> int:
    response = client.post(
        "/api/v1/outbound-docs/warehouse-confirm",
        json={
            "contract_id": contract_id,
            "sales_order_id": sales_order_id,
            "source_ticket_no": source_ticket_no,
            "actual_qty": float(actual_qty),
            "warehouse_id": "CODEX-TEST-WH-001",
        },
        headers=_warehouse_headers(
            auth_headers,
            f"CODEX-TEST-D01-INV-WH-{uuid4().hex[:6]}",
        ),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_manual_outbound_doc(
    auth_headers,
    *,
    contract_id: int,
    sales_order_id: int,
    oil_product_id: str,
    manual_ref_no: str,
    actual_qty: Decimal,
) -> int:
    response = client.post(
        "/api/v1/outbound-docs/manual",
        json={
            "contract_id": contract_id,
            "sales_order_id": sales_order_id,
            "oil_product_id": oil_product_id,
            "manual_ref_no": manual_ref_no,
            "actual_qty": float(actual_qty),
            "reason": "D01 仓储主链手工补录校验失败验证",
        },
        headers=_operations_headers(auth_headers, "CODEX-TEST-D01-INV-MANUAL-CREATE"),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _finance_headers(auth_headers, user_id: str) -> dict[str, str]:
    return auth_headers(
        user_id=user_id,
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )


def _operations_headers(auth_headers, user_id: str) -> dict[str, str]:
    return auth_headers(
        user_id=user_id,
        role_code="operations",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )


def _warehouse_headers(auth_headers, user_id: str) -> dict[str, str]:
    return auth_headers(
        user_id=user_id,
        role_code="warehouse",
        company_id="CODEX-TEST-WAREHOUSE-COMPANY",
        company_type="warehouse_company",
        client_type="miniprogram",
    )


def _customer_headers(auth_headers, user_id: str) -> dict[str, str]:
    return auth_headers(
        user_id=user_id,
        role_code="customer",
        company_id=CUSTOMER_COMPANY_ID,
        company_type="customer_company",
        client_type="miniprogram",
    )
