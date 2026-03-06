from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.contract import Contract
from app.models.contract_effective_task import ContractEffectiveTask
from app.models.contract_item import ContractItem
from app.models.contract_qty_effect import ContractQtyEffect
from app.models.doc_relation import DocRelation
from app.models.inbound_doc import InboundDoc
from app.models.outbound_doc import OutboundDoc

client = TestClient(app)

CUSTOMER_COMPANY_ID = "CODEX-TEST-CUSTOMER-COMPANY"
SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"


def test_purchase_contract_approve_materializes_inbound_docs_per_item(auth_headers) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        items=[
            {"oil_product_id": "OIL-92", "qty_signed": Decimal("100.000"), "unit_price": Decimal("6300.80")},
            {"oil_product_id": "OIL-95", "qty_signed": Decimal("80.000"), "unit_price": Decimal("6400.10")},
        ],
    )

    inbound_docs = _query_inbound_docs(contract_id=contract_id)
    assert len(inbound_docs) == 2
    assert {doc.oil_product_id for doc in inbound_docs} == {"OIL-92", "OIL-95"}
    assert {doc.source_type for doc in inbound_docs} == {"AUTO_CONTRACT"}
    assert {doc.status for doc in inbound_docs} == {"草稿"}

    tasks = _query_contract_tasks(contract_id=contract_id)
    assert {task.status for task in tasks if task.target_doc_type == "inbound_doc"} == {"已生成"}
    assert _relation_exists("contract", contract_id, "inbound_doc", inbound_docs[0].id, "GENERATES")
    assert _relation_exists("contract", contract_id, "inbound_doc", inbound_docs[1].id, "GENERATES")


def test_submit_inbound_doc_updates_qty_in_acc_and_marks_contract_qty_done(auth_headers) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        items=[{"oil_product_id": "OIL-92", "qty_signed": Decimal("100.000"), "unit_price": Decimal("6300.80")}],
    )
    inbound_doc = _query_inbound_docs(contract_id=contract_id)[0]

    response = client.post(
        f"/api/v1/inbound-docs/{inbound_doc.id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-INBOUND-SUBMIT"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "已过账"
    contract = _query_contract(contract_id)
    assert contract is not None
    assert contract.status == "数量履约完成"
    contract_item = _query_contract_item(contract_id=contract_id, oil_product_id="OIL-92")
    assert contract_item is not None
    assert contract_item.qty_in_acc == Decimal("100.000")
    assert _query_qty_effects("inbound_doc", inbound_doc.id, "IN") == [Decimal("100.000")]


def test_submit_inbound_doc_blocks_threshold_overflow(auth_headers) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        items=[{"oil_product_id": "OIL-92", "qty_signed": Decimal("100.000"), "unit_price": Decimal("6300.80")}],
    )
    inbound_doc = _query_inbound_docs(contract_id=contract_id)[0]

    response = client.post(
        f"/api/v1/inbound-docs/{inbound_doc.id}/submit",
        json={"actual_qty": 106, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-INBOUND-BLOCK"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "校验失败"
    contract_item = _query_contract_item(contract_id=contract_id, oil_product_id="OIL-92")
    assert contract_item is not None
    assert contract_item.qty_in_acc == Decimal("0.000")


def test_warehouse_confirm_creates_outbound_doc_pending_submit(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        items=[{"oil_product_id": "OIL-92", "qty_signed": Decimal("100.000"), "unit_price": Decimal("6300.80")}],
    )
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
    )

    response = client.post(
        "/api/v1/outbound-docs/warehouse-confirm",
        json={
            "contract_id": sales_contract_id,
            "sales_order_id": sales_order_id,
            "source_ticket_no": "CODEX-TEST-SYS-TICKET-001",
            "actual_qty": 10,
            "warehouse_id": "CODEX-TEST-WH-001",
        },
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-OUTBOUND-CREATE"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "待提交"
    outbound_doc = _query_outbound_docs(sales_order_id=sales_order_id)[0]
    assert outbound_doc.source_type == "SYSTEM"
    assert outbound_doc.source_ticket_no == "CODEX-TEST-SYS-TICKET-001"
    assert _relation_exists("sales_order", sales_order_id, "outbound_doc", outbound_doc.id, "GENERATES")


def test_manual_outbound_requires_matching_contract_order_and_oil(auth_headers) -> None:
    sales_contract_id_a = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    sales_contract_id_b = _create_effective_sales_contract(
        auth_headers,
        qty_signed=Decimal("100.000"),
        customer_id="CODEX-TEST-CUSTOMER-COMPANY-B",
    )
    sales_order_id = _create_sales_order_draft(auth_headers, sales_contract_id=sales_contract_id_a, qty=Decimal("50.000"))

    response = client.post(
        "/api/v1/outbound-docs/manual",
        json={
            "contract_id": sales_contract_id_b,
            "sales_order_id": sales_order_id,
            "oil_product_id": "OIL-92",
            "manual_ref_no": "CODEX-TEST-MANUAL-001",
            "actual_qty": 10,
            "reason": "手工补录测试",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-MANUAL-OUTBOUND-MISMATCH",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "销售合同与销售订单不匹配，禁止生成出库单"


def test_warehouse_confirm_requires_sales_order_ready_for_execution(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    sales_order_id = _create_sales_order_draft(
        auth_headers,
        sales_contract_id=sales_contract_id,
        qty=Decimal("30.000"),
    )

    response = client.post(
        "/api/v1/outbound-docs/warehouse-confirm",
        json={
            "contract_id": sales_contract_id,
            "sales_order_id": sales_order_id,
            "source_ticket_no": "CODEX-TEST-SYS-TICKET-NOT-READY",
            "actual_qty": 10,
            "warehouse_id": "CODEX-TEST-WH-001",
        },
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-NOT-READY"),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "销售订单未进入执行阶段，禁止生成出库单"


def test_manual_outbound_requires_sales_order_ready_for_execution(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    sales_order_id = _create_sales_order_draft(
        auth_headers,
        sales_contract_id=sales_contract_id,
        qty=Decimal("30.000"),
    )

    response = client.post(
        "/api/v1/outbound-docs/manual",
        json={
            "contract_id": sales_contract_id,
            "sales_order_id": sales_order_id,
            "oil_product_id": "OIL-92",
            "manual_ref_no": "CODEX-TEST-MANUAL-NOT-READY",
            "actual_qty": 10,
            "reason": "补录测试",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-OPS-MANUAL-NOT-READY",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "销售订单未进入执行阶段，禁止生成出库单"


def test_submit_outbound_doc_updates_qty_out_acc(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        items=[{"oil_product_id": "OIL-92", "qty_signed": Decimal("100.000"), "unit_price": Decimal("6300.80")}],
    )
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
    )
    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-SYS-TICKET-002",
        actual_qty=Decimal("60.000"),
    )

    submit_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 60, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-OUTBOUND-SUBMIT"),
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "已过账"
    contract_item = _query_contract_item(contract_id=sales_contract_id, oil_product_id="OIL-92")
    assert contract_item is not None
    assert contract_item.qty_out_acc == Decimal("60.000")
    assert _query_qty_effects("outbound_doc", outbound_doc_id, "OUT") == [Decimal("60.000")]


def test_submit_outbound_doc_blocks_threshold_overflow(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        items=[{"oil_product_id": "OIL-92", "qty_signed": Decimal("100.000"), "unit_price": Decimal("6300.80")}],
    )
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
    )
    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-SYS-TICKET-003",
        actual_qty=Decimal("106.000"),
    )

    submit_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 106, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-OUTBOUND-BLOCK"),
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "校验失败"
    contract_item = _query_contract_item(contract_id=sales_contract_id, oil_product_id="OIL-92")
    assert contract_item is not None
    assert contract_item.qty_out_acc == Decimal("0.000")


def test_contract_qty_done_blocks_new_outbound_submit(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        items=[{"oil_product_id": "OIL-92", "qty_signed": Decimal("100.000"), "unit_price": Decimal("6300.80")}],
    )
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
    )

    first_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-SYS-TICKET-004",
        actual_qty=Decimal("100.000"),
    )
    first_submit = client.post(
        f"/api/v1/outbound-docs/{first_doc_id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-QTY-DONE-1"),
    )
    assert first_submit.status_code == 200
    assert first_submit.json()["status"] == "已过账"

    second_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-SYS-TICKET-005",
        actual_qty=Decimal("1.000"),
    )
    second_submit = client.post(
        f"/api/v1/outbound-docs/{second_doc_id}/submit",
        json={"actual_qty": 1, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-QTY-DONE-2"),
    )

    assert second_submit.status_code == 200
    assert second_submit.json()["status"] == "已终止"
    contract = _query_contract(sales_contract_id)
    assert contract is not None
    assert contract.status == "数量履约完成"


def test_repeated_outbound_submit_is_idempotent(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers,
        supplier_id=SUPPLIER_COMPANY_ID,
        items=[{"oil_product_id": "OIL-92", "qty_signed": Decimal("100.000"), "unit_price": Decimal("6300.80")}],
    )
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
    )
    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-SYS-TICKET-006",
        actual_qty=Decimal("20.000"),
    )

    first_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 20, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-IDEMPOTENT-1"),
    )
    second_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 20, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-WAREHOUSE-IDEMPOTENT-2"),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["message"] == "出库单已过账，无需重复提交"
    assert _query_qty_effects("outbound_doc", outbound_doc_id, "OUT") == [Decimal("20.000")]


def _query_inbound_docs(*, contract_id: int | None = None) -> list[InboundDoc]:
    with SessionLocal() as db:
        statement = select(InboundDoc)
        if contract_id is not None:
            statement = statement.where(InboundDoc.contract_id == contract_id)
        return list(db.scalars(statement.order_by(InboundDoc.id)).all())


def _query_outbound_docs(*, sales_order_id: int | None = None, contract_id: int | None = None) -> list[OutboundDoc]:
    with SessionLocal() as db:
        statement = select(OutboundDoc)
        if sales_order_id is not None:
            statement = statement.where(OutboundDoc.sales_order_id == sales_order_id)
        if contract_id is not None:
            statement = statement.where(OutboundDoc.contract_id == contract_id)
        return list(db.scalars(statement.order_by(OutboundDoc.id)).all())


def _query_contract(contract_id: int) -> Contract | None:
    with SessionLocal() as db:
        return db.get(Contract, contract_id)


def _query_contract_item(*, contract_id: int, oil_product_id: str) -> ContractItem | None:
    with SessionLocal() as db:
        statement = select(ContractItem).where(
            ContractItem.contract_id == contract_id,
            ContractItem.oil_product_id == oil_product_id,
        )
        return db.scalar(statement)


def _query_contract_tasks(*, contract_id: int) -> list[ContractEffectiveTask]:
    with SessionLocal() as db:
        statement = (
            select(ContractEffectiveTask)
            .where(ContractEffectiveTask.contract_id == contract_id)
            .order_by(ContractEffectiveTask.id)
        )
        return list(db.scalars(statement).all())


def _query_qty_effects(doc_type: str, doc_id: int, effect_type: str) -> list[Decimal]:
    with SessionLocal() as db:
        statement = (
            select(ContractQtyEffect.effect_qty)
            .where(
                ContractQtyEffect.doc_type == doc_type,
                ContractQtyEffect.doc_id == doc_id,
                ContractQtyEffect.effect_type == effect_type,
            )
            .order_by(ContractQtyEffect.id)
        )
        return list(db.scalars(statement).all())


def _relation_exists(
    source_doc_type: str,
    source_doc_id: int,
    target_doc_type: str,
    target_doc_id: int,
    relation_type: str,
) -> bool:
    with SessionLocal() as db:
        statement = select(DocRelation.id).where(
            DocRelation.source_doc_type == source_doc_type,
            DocRelation.source_doc_id == source_doc_id,
            DocRelation.target_doc_type == target_doc_type,
            DocRelation.target_doc_id == target_doc_id,
            DocRelation.relation_type == relation_type,
        )
        return db.scalar(statement) is not None


def _create_effective_purchase_contract(auth_headers, *, supplier_id: str, items: list[dict]) -> int:
    create_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": f"CODEX-TEST-M5-PURCHASE-{uuid4().hex[:10]}",
            "supplier_id": supplier_id,
            "items": [
                {
                    "oil_product_id": item["oil_product_id"],
                    "qty_signed": float(item["qty_signed"]),
                    "unit_price": float(item["unit_price"]),
                }
                for item in items
            ],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M5-FINANCE-CREATE-PURCHASE-CONTRACT",
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
        json={"comment": "M5采购合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M5采购合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_effective_sales_contract(
    auth_headers,
    *,
    qty_signed: Decimal,
    customer_id: str = CUSTOMER_COMPANY_ID,
    unit_price: Decimal = Decimal("6500.25"),
) -> int:
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-M5-SALES-{uuid4().hex[:10]}",
            "customer_id": customer_id,
            "items": [{"oil_product_id": "OIL-92", "qty_signed": float(qty_signed), "unit_price": float(unit_price)}],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M5-FINANCE-CREATE-SALES-CONTRACT",
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
        json={"comment": "M5销售合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M5销售合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_sales_order_draft(auth_headers, *, sales_contract_id: int, qty: Decimal) -> int:
    response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": float(qty),
            "unit_price": 6500.25,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M5-CUSTOMER-CREATE-ORDER",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_sales_order_derived(
    auth_headers,
    *,
    sales_contract_id: int,
    purchase_contract_id: int,
    qty: Decimal,
    actual_receipt_amount: Decimal = Decimal("12000.34"),
    actual_pay_amount: Decimal = Decimal("11800.12"),
) -> int:
    sales_order_id = _create_sales_order_draft(auth_headers, sales_contract_id=sales_contract_id, qty=qty)

    submit_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/submit",
        json={"comment": "M5自动化提交"},
        headers=auth_headers(
            user_id="CODEX-TEST-M5-CUSTOMER-SUBMIT",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert submit_response.status_code == 200

    ops_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "M5运营审批通过"},
        headers=auth_headers(
            user_id="CODEX-TEST-M5-OPS-APPROVE",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert ops_response.status_code == 200

    finance_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": float(actual_receipt_amount),
            "actual_pay_amount": float(actual_pay_amount),
            "comment": "M5财务审批通过",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M5-FINANCE-APPROVE",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
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
        headers=_warehouse_headers(auth_headers, f"CODEX-TEST-WAREHOUSE-{uuid4().hex[:8]}"),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _warehouse_headers(auth_headers, user_id: str) -> dict[str, str]:
    return auth_headers(
        user_id=user_id,
        role_code="warehouse",
        company_id="CODEX-TEST-WAREHOUSE-COMPANY",
        company_type="warehouse_company",
        client_type="miniprogram",
    )
