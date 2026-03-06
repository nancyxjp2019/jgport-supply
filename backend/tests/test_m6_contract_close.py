from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.contract import Contract
from app.models.inbound_doc import InboundDoc
from app.models.outbound_doc import OutboundDoc
from app.models.payment_doc import PaymentDoc
from app.models.receipt_doc import ReceiptDoc

client = TestClient(app)

CUSTOMER_COMPANY_ID = "CODEX-TEST-CUSTOMER-COMPANY"
SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"
RECEIPT_VOUCHER = ["CODEX-TEST-/receipt-voucher-001.jpg"]
PAYMENT_VOUCHER = ["CODEX-TEST-/payment-voucher-001.jpg"]


def test_sales_contract_auto_closes_after_qty_done_and_receipt_closed(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(auth_headers, qty_signed=Decimal("100.000"))
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("600025.00"),
        actual_pay_amount=Decimal("580080.00"),
    )

    deposit_receipt_doc = _query_receipt_docs(contract_id=sales_contract_id, doc_type="DEPOSIT")[0]
    normal_receipt_doc = _query_receipt_docs(contract_id=sales_contract_id, sales_order_id=sales_order_id, doc_type="NORMAL")[0]
    _confirm_receipt_doc(auth_headers, receipt_doc_id=deposit_receipt_doc.id, amount_actual=Decimal("50000.00"))
    _confirm_receipt_doc(auth_headers, receipt_doc_id=normal_receipt_doc.id, amount_actual=Decimal("600025.00"))

    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-M6-SALES-CLOSE-001",
        actual_qty=Decimal("100.000"),
    )
    submit_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-M6-WH-SALES-AUTO-CLOSE"),
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["message"] == "出库单已过账，合同已自动关闭"
    contract = _query_contract(sales_contract_id)
    assert contract is not None
    assert contract.status == "已关闭"
    assert contract.close_type == "AUTO"
    assert contract.closed_by == "CODEX-TEST-M6-WH-SALES-AUTO-CLOSE"


def test_purchase_contract_auto_closes_after_qty_done_and_payment_closed(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(auth_headers, qty_signed=Decimal("100.000"))
    _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("600025.00"),
        actual_pay_amount=Decimal("580080.00"),
    )

    deposit_payment_doc = _query_payment_docs(contract_id=purchase_contract_id, doc_type="DEPOSIT")[0]
    normal_payment_doc = _query_payment_docs(contract_id=purchase_contract_id, doc_type="NORMAL")[0]
    _confirm_payment_doc(auth_headers, payment_doc_id=deposit_payment_doc.id, amount_actual=Decimal("50000.00"))
    _confirm_payment_doc(auth_headers, payment_doc_id=normal_payment_doc.id, amount_actual=Decimal("580080.00"))

    inbound_doc = _query_inbound_docs(contract_id=purchase_contract_id)[0]
    submit_response = client.post(
        f"/api/v1/inbound-docs/{inbound_doc.id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-M6-WH-PURCHASE-AUTO-CLOSE"),
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["message"] == "入库单已过账，合同已自动关闭"
    contract = _query_contract(purchase_contract_id)
    assert contract is not None
    assert contract.status == "已关闭"
    assert contract.close_type == "AUTO"


def test_qty_done_without_amount_close_keeps_contract_in_qty_done(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(auth_headers, qty_signed=Decimal("100.000"))
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("500000.00"),
        actual_pay_amount=Decimal("580080.00"),
    )

    deposit_receipt_doc = _query_receipt_docs(contract_id=sales_contract_id, doc_type="DEPOSIT")[0]
    normal_receipt_doc = _query_receipt_docs(contract_id=sales_contract_id, sales_order_id=sales_order_id, doc_type="NORMAL")[0]
    _confirm_receipt_doc(auth_headers, receipt_doc_id=deposit_receipt_doc.id, amount_actual=Decimal("50000.00"))
    _confirm_receipt_doc(auth_headers, receipt_doc_id=normal_receipt_doc.id, amount_actual=Decimal("500000.00"))

    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-M6-SALES-QTY-DONE-001",
        actual_qty=Decimal("100.000"),
    )
    submit_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-M6-WH-QTY-DONE"),
    )

    assert submit_response.status_code == 200
    contract = _query_contract(sales_contract_id)
    assert contract is not None
    assert contract.status == "数量履约完成"
    assert contract.close_type is None


def test_manual_close_requires_qty_done(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    response = client.post(
        f"/api/v1/contracts/{sales_contract_id}/manual-close",
        json={"reason": "未完成数量前禁止关闭", "confirm_token": "MANUAL_CLOSE"},
        headers=auth_headers(
            user_id="CODEX-TEST-M6-FINANCE-MANUAL-CLOSE-BLOCK",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "合同未达到数量履约完成，禁止手工关闭"


def test_manual_close_terminates_open_docs_and_blocks_future_supplement(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(auth_headers, qty_signed=Decimal("100.000"))
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("500000.00"),
        actual_pay_amount=Decimal("580080.00"),
    )

    deposit_receipt_doc = _query_receipt_docs(contract_id=sales_contract_id, doc_type="DEPOSIT")[0]
    _confirm_receipt_doc(auth_headers, receipt_doc_id=deposit_receipt_doc.id, amount_actual=Decimal("50000.00"))

    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-M6-SALES-MANUAL-CLOSE-001",
        actual_qty=Decimal("100.000"),
    )
    submit_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-M6-WH-MANUAL-CLOSE-1"),
    )
    assert submit_response.status_code == 200

    draft_receipt_response = client.post(
        "/api/v1/receipt-docs/supplement",
        json={"contract_id": sales_contract_id, "sales_order_id": sales_order_id, "amount_actual": 1.0},
        headers=auth_headers(
            user_id="CODEX-TEST-M6-FINANCE-RECEIPT-DRAFT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert draft_receipt_response.status_code == 200
    draft_receipt_doc_id = draft_receipt_response.json()["id"]

    pending_outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-M6-SALES-MANUAL-CLOSE-002",
        actual_qty=Decimal("1.000"),
    )

    manual_close_response = client.post(
        f"/api/v1/contracts/{sales_contract_id}/manual-close",
        json={"reason": "金额未闭环，执行手工关闭", "confirm_token": "MANUAL_CLOSE"},
        headers=auth_headers(
            user_id="CODEX-TEST-M6-FINANCE-MANUAL-CLOSE",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert manual_close_response.status_code == 200
    body = manual_close_response.json()
    assert body["status"] == "手工关闭"
    assert body["close_type"] == "MANUAL"
    assert Decimal(str(body["manual_close_diff_amount"])) == Decimal("600025.00")
    assert body["manual_close_reason"] == "金额未闭环，执行手工关闭"
    assert _query_receipt_doc(draft_receipt_doc_id).status == "已终止"
    assert _query_outbound_doc(pending_outbound_doc_id).status == "已终止"

    blocked_response = client.post(
        "/api/v1/receipt-docs/supplement",
        json={"contract_id": sales_contract_id, "sales_order_id": sales_order_id, "amount_actual": 2.0},
        headers=auth_headers(
            user_id="CODEX-TEST-M6-FINANCE-RECEIPT-BLOCK",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert blocked_response.status_code == 409
    assert blocked_response.json()["detail"] == "合同已关闭，禁止继续补录或确认资金单据"


def test_auto_close_terminates_open_draft_docs(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(auth_headers, qty_signed=Decimal("100.000"))
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("600025.00"),
        actual_pay_amount=Decimal("580080.00"),
    )

    draft_receipt_response = client.post(
        "/api/v1/receipt-docs/supplement",
        json={"contract_id": sales_contract_id, "sales_order_id": sales_order_id, "amount_actual": 1.0},
        headers=auth_headers(
            user_id="CODEX-TEST-M6-FINANCE-RECEIPT-DRAFT-AUTO",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert draft_receipt_response.status_code == 200
    draft_receipt_doc_id = draft_receipt_response.json()["id"]

    deposit_receipt_doc = _query_receipt_docs(contract_id=sales_contract_id, doc_type="DEPOSIT")[0]
    normal_receipt_doc = _query_receipt_docs(contract_id=sales_contract_id, sales_order_id=sales_order_id, doc_type="NORMAL")[0]
    _confirm_receipt_doc(auth_headers, receipt_doc_id=deposit_receipt_doc.id, amount_actual=Decimal("50000.00"))
    _confirm_receipt_doc(auth_headers, receipt_doc_id=normal_receipt_doc.id, amount_actual=Decimal("600025.00"))

    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-M6-SALES-AUTO-TERM-001",
        actual_qty=Decimal("100.000"),
    )
    submit_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-M6-WH-AUTO-TERM"),
    )

    assert submit_response.status_code == 200
    assert _query_receipt_doc(draft_receipt_doc_id).status == "已终止"


def test_manual_close_requires_valid_confirm_token(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(auth_headers, qty_signed=Decimal("100.000"))
    purchase_contract_id = _create_effective_purchase_contract(auth_headers, qty_signed=Decimal("100.000"))
    sales_order_id = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("500000.00"),
        actual_pay_amount=Decimal("580080.00"),
    )
    deposit_receipt_doc = _query_receipt_docs(contract_id=sales_contract_id, doc_type="DEPOSIT")[0]
    _confirm_receipt_doc(auth_headers, receipt_doc_id=deposit_receipt_doc.id, amount_actual=Decimal("50000.00"))
    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no="CODEX-TEST-M6-SALES-BAD-TOKEN-001",
        actual_qty=Decimal("100.000"),
    )
    submit_response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": 100, "warehouse_id": "CODEX-TEST-WH-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-M6-WH-BAD-TOKEN"),
    )
    assert submit_response.status_code == 200

    response = client.post(
        f"/api/v1/contracts/{sales_contract_id}/manual-close",
        json={"reason": "错误口令", "confirm_token": "bad-token"},
        headers=auth_headers(
            user_id="CODEX-TEST-M6-FINANCE-BAD-TOKEN",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "手工关闭确认口令不正确"


def _query_contract(contract_id: int) -> Contract | None:
    with SessionLocal() as db:
        return db.get(Contract, contract_id)


def _query_receipt_docs(
    *,
    contract_id: int | None = None,
    sales_order_id: int | None = None,
    doc_type: str | None = None,
) -> list[ReceiptDoc]:
    with SessionLocal() as db:
        statement = select(ReceiptDoc)
        if contract_id is not None:
            statement = statement.where(ReceiptDoc.contract_id == contract_id)
        if sales_order_id is not None:
            statement = statement.where(ReceiptDoc.sales_order_id == sales_order_id)
        if doc_type is not None:
            statement = statement.where(ReceiptDoc.doc_type == doc_type)
        return list(db.scalars(statement.order_by(ReceiptDoc.id)).all())


def _query_payment_docs(
    *,
    contract_id: int | None = None,
    purchase_order_id: int | None = None,
    doc_type: str | None = None,
) -> list[PaymentDoc]:
    with SessionLocal() as db:
        statement = select(PaymentDoc)
        if contract_id is not None:
            statement = statement.where(PaymentDoc.contract_id == contract_id)
        if purchase_order_id is not None:
            statement = statement.where(PaymentDoc.purchase_order_id == purchase_order_id)
        if doc_type is not None:
            statement = statement.where(PaymentDoc.doc_type == doc_type)
        return list(db.scalars(statement.order_by(PaymentDoc.id)).all())


def _query_receipt_doc(receipt_doc_id: int) -> ReceiptDoc:
    with SessionLocal() as db:
        receipt_doc = db.get(ReceiptDoc, receipt_doc_id)
        assert receipt_doc is not None
        return receipt_doc


def _query_outbound_doc(outbound_doc_id: int) -> OutboundDoc:
    with SessionLocal() as db:
        outbound_doc = db.get(OutboundDoc, outbound_doc_id)
        assert outbound_doc is not None
        return outbound_doc


def _query_inbound_docs(*, contract_id: int) -> list[InboundDoc]:
    with SessionLocal() as db:
        statement = select(InboundDoc).where(InboundDoc.contract_id == contract_id).order_by(InboundDoc.id)
        return list(db.scalars(statement).all())


def _confirm_receipt_doc(auth_headers, *, receipt_doc_id: int, amount_actual: Decimal) -> None:
    response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc_id}/confirm",
        json={"amount_actual": float(amount_actual), "voucher_files": RECEIPT_VOUCHER},
        headers=auth_headers(
            user_id=f"CODEX-TEST-M6-FINANCE-RECEIPT-{uuid4().hex[:8]}",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200


def _confirm_payment_doc(auth_headers, *, payment_doc_id: int, amount_actual: Decimal) -> None:
    response = client.post(
        f"/api/v1/payment-docs/{payment_doc_id}/confirm",
        json={"amount_actual": float(amount_actual), "voucher_files": PAYMENT_VOUCHER},
        headers=auth_headers(
            user_id=f"CODEX-TEST-M6-FINANCE-PAYMENT-{uuid4().hex[:8]}",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert response.status_code == 200


def _create_effective_sales_contract(
    auth_headers,
    *,
    qty_signed: Decimal,
    unit_price: Decimal = Decimal("6500.25"),
    customer_id: str = CUSTOMER_COMPANY_ID,
) -> int:
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-M6-SALES-{uuid4().hex[:10]}",
            "customer_id": customer_id,
            "items": [{"oil_product_id": "OIL-92", "qty_signed": float(qty_signed), "unit_price": float(unit_price)}],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M6-FINANCE-CREATE-SALES",
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
        json={"comment": "M6销售合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M6销售合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_effective_purchase_contract(
    auth_headers,
    *,
    qty_signed: Decimal,
    unit_price: Decimal = Decimal("6300.80"),
) -> int:
    create_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": f"CODEX-TEST-M6-PURCHASE-{uuid4().hex[:10]}",
            "supplier_id": SUPPLIER_COMPANY_ID,
            "items": [{"oil_product_id": "OIL-92", "qty_signed": float(qty_signed), "unit_price": float(unit_price)}],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M6-FINANCE-CREATE-PURCHASE",
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
        json={"comment": "M6采购合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M6采购合同生效"},
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
    actual_receipt_amount: Decimal,
    actual_pay_amount: Decimal,
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
            user_id=f"CODEX-TEST-M6-CUSTOMER-{uuid4().hex[:8]}",
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
        json={"comment": "M6自动提交"},
        headers=auth_headers(
            user_id=f"CODEX-TEST-M6-CUSTOMER-SUBMIT-{uuid4().hex[:8]}",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert submit_response.status_code == 200

    ops_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "M6运营审批通过"},
        headers=auth_headers(
            user_id=f"CODEX-TEST-M6-OPS-{uuid4().hex[:8]}",
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
            "comment": "M6财务审批通过",
        },
        headers=auth_headers(
            user_id=f"CODEX-TEST-M6-FINANCE-{uuid4().hex[:8]}",
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
        headers=_warehouse_headers(auth_headers, f"CODEX-TEST-M6-WH-{uuid4().hex[:8]}"),
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
