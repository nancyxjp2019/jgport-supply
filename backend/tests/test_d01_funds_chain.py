from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.payment_doc import PaymentDoc
from app.models.receipt_doc import ReceiptDoc

client = TestClient(app)

CUSTOMER_COMPANY_ID = "CODEX-TEST-CUSTOMER-COMPANY"
SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"


def test_d01_funds_chain_pending_supplement_refund_and_writeoff(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    deposit_receipt_doc = _query_receipt_docs(
        contract_id=sales_contract_id, doc_type="DEPOSIT"
    )[0]
    deposit_payment_doc = _query_payment_docs(
        contract_id=purchase_contract_id, doc_type="DEPOSIT"
    )[0]

    confirm_deposit_receipt_response = client.post(
        f"/api/v1/receipt-docs/{deposit_receipt_doc.id}/confirm",
        json={
            "amount_actual": 50000.00,
            "voucher_files": ["CODEX-TEST-/d01-receipt-deposit-voucher.png"],
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-RECEIPT-DEPOSIT"),
    )
    assert confirm_deposit_receipt_response.status_code == 200
    assert confirm_deposit_receipt_response.json()["status"] == "已确认"
    assert confirm_deposit_receipt_response.json()["voucher_file_paths"] == [
        "CODEX-TEST-/d01-receipt-deposit-voucher.png"
    ]

    confirm_deposit_payment_response = client.post(
        f"/api/v1/payment-docs/{deposit_payment_doc.id}/confirm",
        json={
            "amount_actual": 48000.00,
            "voucher_files": ["CODEX-TEST-/d01-payment-deposit-voucher.png"],
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-PAYMENT-DEPOSIT"),
    )
    assert confirm_deposit_payment_response.status_code == 200
    assert confirm_deposit_payment_response.json()["status"] == "已确认"
    assert confirm_deposit_payment_response.json()["voucher_file_paths"] == [
        "CODEX-TEST-/d01-payment-deposit-voucher.png"
    ]

    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )
    finance_approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 0,
            "actual_pay_amount": 6000.00,
            "comment": "D01 收付款主链联调",
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-FUNDS-ORDER"),
    )
    assert finance_approve_response.status_code == 200
    purchase_order_id = finance_approve_response.json()["purchase_order_id"]
    assert purchase_order_id is not None

    normal_receipt_doc = _query_receipt_docs(
        sales_order_id=sales_order_id, doc_type="NORMAL"
    )[0]
    pending_receipt_response = client.post(
        f"/api/v1/receipt-docs/{normal_receipt_doc.id}/confirm",
        json={"amount_actual": 0, "voucher_files": []},
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-RECEIPT-PENDING"),
    )
    assert pending_receipt_response.status_code == 200
    assert pending_receipt_response.json()["status"] == "待补录金额"

    refill_receipt_response = client.post(
        f"/api/v1/receipt-docs/{normal_receipt_doc.id}/confirm",
        json={
            "amount_actual": 8800.45,
            "voucher_files": ["CODEX-TEST-/d01-receipt-backfill-voucher.png"],
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-RECEIPT-REFILL"),
    )
    assert refill_receipt_response.status_code == 200
    assert refill_receipt_response.json()["status"] == "已确认"
    assert refill_receipt_response.json()["voucher_file_paths"] == [
        "CODEX-TEST-/d01-receipt-backfill-voucher.png"
    ]

    normal_payment_doc = _query_payment_docs(
        purchase_order_id=purchase_order_id, doc_type="NORMAL"
    )[0]
    confirm_payment_response = client.post(
        f"/api/v1/payment-docs/{normal_payment_doc.id}/confirm",
        json={
            "amount_actual": 6000.00,
            "voucher_files": [
                "CODEX-TEST-/d01-payment-normal-voucher-a.png",
                "CODEX-TEST-/d01-payment-normal-voucher-b.png",
            ],
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-PAYMENT-CONFIRM"),
    )
    assert confirm_payment_response.status_code == 200
    assert confirm_payment_response.json()["status"] == "已确认"

    refund_request_response = client.post(
        f"/api/v1/payment-docs/{normal_payment_doc.id}/refund-request",
        json={"refund_amount": 1000.00, "reason": "CODEX-TEST-D01-付款退款申请"},
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-PAYMENT-REFUND-REQ1"),
    )
    assert refund_request_response.status_code == 200
    assert refund_request_response.json()["refund_status"] == "待审核"

    refund_reject_response = client.post(
        f"/api/v1/payment-docs/{normal_payment_doc.id}/refund-reject",
        json={"reason": "CODEX-TEST-D01-付款退款驳回"},
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-PAYMENT-REFUND-REJECT"),
    )
    assert refund_reject_response.status_code == 200
    assert refund_reject_response.json()["refund_status"] == "驳回"
    assert Decimal(str(refund_reject_response.json()["refund_amount"])) == Decimal(
        "0.00"
    )

    refund_request_again_response = client.post(
        f"/api/v1/payment-docs/{normal_payment_doc.id}/refund-request",
        json={"refund_amount": 1000.00, "reason": "CODEX-TEST-D01-付款退款复提"},
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-PAYMENT-REFUND-REQ2"),
    )
    assert refund_request_again_response.status_code == 200
    assert refund_request_again_response.json()["refund_status"] == "待审核"

    refund_approve_response = client.post(
        f"/api/v1/payment-docs/{normal_payment_doc.id}/refund-approve",
        json={"reason": "CODEX-TEST-D01-付款退款审核通过"},
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-PAYMENT-REFUND-APPROVE"),
    )
    assert refund_approve_response.status_code == 200
    assert refund_approve_response.json()["refund_status"] == "部分退款"

    writeoff_response = client.post(
        f"/api/v1/payment-docs/{normal_payment_doc.id}/writeoff",
        json={"comment": "CODEX-TEST-D01-付款核销"},
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-PAYMENT-WRITEOFF"),
    )
    assert writeoff_response.status_code == 200
    assert writeoff_response.json()["status"] == "已核销"

    refreshed_receipt_doc = _query_receipt_docs(
        sales_order_id=sales_order_id, doc_type="NORMAL"
    )[0]
    refreshed_payment_doc = _query_payment_docs(
        purchase_order_id=purchase_order_id, doc_type="NORMAL"
    )[0]
    assert refreshed_receipt_doc.amount_actual == Decimal("8800.45")
    assert refreshed_receipt_doc.status == "已确认"
    assert refreshed_payment_doc.amount_actual == Decimal("6000.00")
    assert refreshed_payment_doc.status == "已核销"
    assert refreshed_payment_doc.refund_status == "部分退款"


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
            statement = statement.where(
                PaymentDoc.purchase_order_id == purchase_order_id
            )
        if doc_type is not None:
            statement = statement.where(PaymentDoc.doc_type == doc_type)
        return list(db.scalars(statement.order_by(PaymentDoc.id)).all())


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


def _create_effective_sales_contract(auth_headers, *, customer_id: str) -> int:
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-D01-FUNDS-SALES-{uuid4().hex[:10]}",
            "customer_id": customer_id,
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 300, "unit_price": 6500.25}
            ],
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-FUNDS-SALES-CREATE"),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "D01 收款合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "D01 收款合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_effective_purchase_contract(auth_headers, *, supplier_id: str) -> int:
    create_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": f"CODEX-TEST-D01-FUNDS-PURCHASE-{uuid4().hex[:10]}",
            "supplier_id": supplier_id,
            "items": [
                {"oil_product_id": "OIL-92", "qty_signed": 400, "unit_price": 6300.80}
            ],
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-D01-FUNDS-PURCHASE-CREATE"),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "D01 付款合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "D01 付款合同生效"},
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
            user_id="CODEX-TEST-D01-FUNDS-CUSTOMER-CREATE",
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
        json={"comment": "D01 收付款订单提审"},
        headers=auth_headers(
            user_id="CODEX-TEST-D01-FUNDS-CUSTOMER-SUBMIT",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert submit_response.status_code == 200

    ops_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "D01 收付款订单运营审批通过"},
        headers=auth_headers(
            user_id="CODEX-TEST-D01-FUNDS-OPS",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert ops_response.status_code == 200
    return sales_order_id


def _finance_headers(auth_headers, user_id: str) -> dict[str, str]:
    return auth_headers(
        user_id=user_id,
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )
