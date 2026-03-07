from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.contract_effective_task import ContractEffectiveTask
from app.models.doc_attachment import DocAttachment
from app.models.doc_relation import DocRelation
from app.models.payment_doc import PaymentDoc
from app.models.receipt_doc import ReceiptDoc

client = TestClient(app)

CUSTOMER_COMPANY_ID = "CODEX-TEST-CUSTOMER-COMPANY"
SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"


def test_purchase_contract_approve_materializes_deposit_payment_doc(
    auth_headers,
) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    payment_docs = _query_payment_docs(contract_id=contract_id)
    assert len(payment_docs) == 1
    payment_doc = payment_docs[0]
    assert payment_doc.doc_type == "DEPOSIT"
    assert payment_doc.purchase_order_id is None
    assert payment_doc.status == "草稿"
    assert payment_doc.amount_actual == Decimal("0.00")

    contract_tasks = _query_contract_tasks(contract_id=contract_id)
    assert {
        task.status for task in contract_tasks if task.target_doc_type == "payment_doc"
    } == {"已生成"}
    assert _relation_exists(
        "contract", contract_id, "payment_doc", payment_doc.id, "GENERATES"
    )


def test_sales_contract_approve_materializes_deposit_receipt_doc(auth_headers) -> None:
    contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )

    receipt_docs = _query_receipt_docs(contract_id=contract_id)
    assert len(receipt_docs) == 1
    receipt_doc = receipt_docs[0]
    assert receipt_doc.doc_type == "DEPOSIT"
    assert receipt_doc.sales_order_id is None
    assert receipt_doc.status == "草稿"
    assert receipt_doc.amount_actual == Decimal("0.00")

    contract_tasks = _query_contract_tasks(contract_id=contract_id)
    assert {
        task.status for task in contract_tasks if task.target_doc_type == "receipt_doc"
    } == {"已生成"}
    assert _relation_exists(
        "contract", contract_id, "receipt_doc", receipt_doc.id, "GENERATES"
    )


def test_sales_order_finance_approve_materializes_normal_fund_docs(
    auth_headers,
) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )

    approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 12000.34,
            "actual_pay_amount": 11800.12,
            "comment": "财务通过并生成资金单据",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-M4",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200
    purchase_order_id = approve_response.json()["purchase_order_id"]
    assert purchase_order_id is not None

    receipt_docs = _query_receipt_docs(sales_order_id=sales_order_id, doc_type="NORMAL")
    assert len(receipt_docs) == 1
    assert receipt_docs[0].amount_actual == Decimal("12000.34")

    payment_docs = _query_payment_docs(
        purchase_order_id=purchase_order_id, doc_type="NORMAL"
    )
    assert len(payment_docs) == 1
    assert payment_docs[0].amount_actual == Decimal("11800.12")
    assert payment_docs[0].voucher_required is True

    assert _relation_exists(
        "sales_order", sales_order_id, "purchase_order", purchase_order_id, "DERIVES"
    )
    assert _relation_exists(
        "sales_order", sales_order_id, "receipt_doc", receipt_docs[0].id, "GENERATES"
    )
    assert _relation_exists(
        "purchase_order",
        purchase_order_id,
        "payment_doc",
        payment_docs[0].id,
        "GENERATES",
    )


def test_zero_pay_exception_generates_payment_doc_with_exempt_reason(
    auth_headers,
) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )

    approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 10000,
            "actual_pay_amount": 0,
            "comment": "0付款例外",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-ZERO-PAY-M4",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200
    purchase_order_id = approve_response.json()["purchase_order_id"]
    assert purchase_order_id is not None

    payment_docs = _query_payment_docs(
        purchase_order_id=purchase_order_id, doc_type="NORMAL"
    )
    assert len(payment_docs) == 1
    payment_doc = payment_docs[0]
    assert payment_doc.amount_actual == Decimal("0.00")
    assert payment_doc.voucher_required is False
    assert payment_doc.voucher_exempt_reason == "例外放行（需后补付款单）"


def test_payment_doc_supplement_requires_matching_contract_and_purchase_order(
    auth_headers,
) -> None:
    purchase_contract_id_a = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    purchase_contract_id_b = _create_effective_purchase_contract(
        auth_headers, supplier_id="CODEX-TEST-SUPPLIER-COMPANY-B"
    )
    sales_contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )

    approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id_a,
            "actual_receipt_amount": 9000,
            "actual_pay_amount": 0,
            "comment": "生成采购订单后补录付款",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-SUPP-PAY",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200
    purchase_order_id = approve_response.json()["purchase_order_id"]
    assert purchase_order_id is not None

    mismatch_response = client.post(
        "/api/v1/payment-docs/supplement",
        json={
            "contract_id": purchase_contract_id_b,
            "purchase_order_id": purchase_order_id,
            "amount_actual": 8888.88,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-SUPP-PAY-MISMATCH",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert mismatch_response.status_code == 409
    assert (
        mismatch_response.json()["detail"] == "采购合同与采购订单不匹配，禁止补录付款单"
    )

    success_response = client.post(
        "/api/v1/payment-docs/supplement",
        json={
            "contract_id": purchase_contract_id_a,
            "purchase_order_id": purchase_order_id,
            "amount_actual": 8888.88,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-SUPP-PAY-SUCCESS",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert success_response.status_code == 200
    supplement_doc_id = success_response.json()["id"]
    assert _relation_exists(
        "contract", purchase_contract_id_a, "payment_doc", supplement_doc_id, "BINDS"
    )
    assert _relation_exists(
        "purchase_order", purchase_order_id, "payment_doc", supplement_doc_id, "BINDS"
    )


def test_finance_can_list_and_query_payment_doc_detail(auth_headers) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    payment_doc = _query_payment_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]

    list_response = client.get(
        "/api/v1/payment-docs",
        params={"status": "草稿", "limit": 50},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-FUND-LIST-PAY",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    assert any(item["id"] == payment_doc.id for item in list_body["items"])

    detail_response = client.get(
        f"/api/v1/payment-docs/{payment_doc.id}",
        headers=auth_headers(
            user_id="CODEX-TEST-M8-FUND-DETAIL-PAY",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["id"] == payment_doc.id
    assert detail_body["doc_no"] == payment_doc.doc_no
    assert detail_body["status"] == "草稿"
    assert detail_body["voucher_file_paths"] == []


def test_finance_can_list_and_query_receipt_doc_detail(auth_headers) -> None:
    contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    receipt_doc = _query_receipt_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]

    list_response = client.get(
        "/api/v1/receipt-docs",
        params={"status": "草稿", "limit": 50},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-FUND-LIST-REC",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] >= 1
    assert any(item["id"] == receipt_doc.id for item in list_body["items"])

    detail_response = client.get(
        f"/api/v1/receipt-docs/{receipt_doc.id}",
        headers=auth_headers(
            user_id="CODEX-TEST-M8-FUND-DETAIL-REC",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["id"] == receipt_doc.id
    assert detail_body["doc_no"] == receipt_doc.doc_no
    assert detail_body["status"] == "草稿"
    assert detail_body["voucher_file_paths"] == []


def test_receipt_doc_supplement_requires_matching_contract_and_sales_order(
    auth_headers,
) -> None:
    sales_contract_id_a = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    sales_contract_id_b = _create_effective_sales_contract(
        auth_headers, customer_id="CODEX-TEST-CUSTOMER-COMPANY-B"
    )
    sales_order_id = _create_sales_order_draft(
        auth_headers, sales_contract_id=sales_contract_id_a
    )

    mismatch_response = client.post(
        "/api/v1/receipt-docs/supplement",
        json={
            "contract_id": sales_contract_id_b,
            "sales_order_id": sales_order_id,
            "amount_actual": 7777.66,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-SUPP-RECEIPT-MISMATCH",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert mismatch_response.status_code == 409
    assert (
        mismatch_response.json()["detail"] == "销售合同与销售订单不匹配，禁止补录收款单"
    )

    success_response = client.post(
        "/api/v1/receipt-docs/supplement",
        json={
            "contract_id": sales_contract_id_a,
            "sales_order_id": sales_order_id,
            "amount_actual": 7777.66,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-SUPP-RECEIPT-SUCCESS",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert success_response.status_code == 200
    supplement_doc_id = success_response.json()["id"]
    assert _relation_exists(
        "contract", sales_contract_id_a, "receipt_doc", supplement_doc_id, "BINDS"
    )
    assert _relation_exists(
        "sales_order", sales_order_id, "receipt_doc", supplement_doc_id, "BINDS"
    )


def test_non_zero_receipt_confirm_requires_voucher_files(auth_headers) -> None:
    contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    receipt_doc = _query_receipt_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]

    confirm_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/confirm",
        json={"amount_actual": 1200.00, "voucher_files": []},
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RECEIPT-CONFIRM-BLOCK",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert confirm_response.status_code == 422
    assert confirm_response.json()["detail"] == "非0金额收款单必须上传收款凭证"
    refreshed_doc = _query_receipt_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]
    assert refreshed_doc.status == "草稿"


def test_non_zero_payment_confirm_persists_voucher_attachment(auth_headers) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    payment_doc = _query_payment_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]

    confirm_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/confirm",
        json={
            "amount_actual": 3200.55,
            "voucher_files": [
                "CODEX-TEST-/payment-voucher-001.png",
                "CODEX-TEST-/payment-voucher-001.png",
            ],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-PAYMENT-CONFIRM",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["status"] == "已确认"
    assert body["voucher_file_paths"] == ["CODEX-TEST-/payment-voucher-001.png"]
    refreshed_doc = _query_payment_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]
    assert refreshed_doc.amount_actual == Decimal("3200.55")
    assert refreshed_doc.status == "已确认"
    assert _query_doc_attachments("payment_doc", payment_doc.id, "PAYMENT_VOUCHER") == [
        "CODEX-TEST-/payment-voucher-001.png"
    ]


def test_confirm_blocks_overlong_voucher_path(auth_headers) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    payment_doc = _query_payment_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]
    overlong_path = "CODEX-TEST-/" + ("a" * 600) + ".png"

    confirm_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/confirm",
        json={"amount_actual": 1000.00, "voucher_files": [overlong_path]},
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-PAYMENT-PATH-LIMIT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert confirm_response.status_code == 422
    assert confirm_response.json()["detail"] == "凭证路径长度不能超过512个字符"


def test_zero_amount_receipt_confirm_passes_rule14_when_deposit_cover_is_enough(
    auth_headers,
) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers,
        customer_id=CUSTOMER_COMPANY_ID,
        qty_signed=Decimal("100.000"),
    )
    deposit_receipt_doc = _query_receipt_docs(
        contract_id=sales_contract_id, doc_type="DEPOSIT"
    )[0]
    deposit_confirm_response = client.post(
        f"/api/v1/receipt-docs/{deposit_receipt_doc.id}/confirm",
        json={
            "amount_actual": 650025.00,
            "voucher_files": ["CODEX-TEST-/deposit-receipt-pass.png"],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-DEPOSIT-RECEIPT-PASS",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert deposit_confirm_response.status_code == 200

    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )
    approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 0,
            "actual_pay_amount": 5000,
            "comment": "规则14收款0金额放行",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RULE14-RECEIPT-PASS",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200

    receipt_doc = _query_receipt_docs(sales_order_id=sales_order_id, doc_type="NORMAL")[
        0
    ]
    confirm_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/confirm",
        json={"amount_actual": 0, "voucher_files": []},
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RULE14-RECEIPT-PASS-CONFIRM",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["status"] == "已确认"
    assert body["voucher_required"] is False
    assert body["voucher_exempt_reason"] == "保证金覆盖放行（规则14）"


def test_zero_amount_receipt_confirm_moves_to_pending_supplement_when_rule14_fails(
    auth_headers,
) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )
    approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 0,
            "actual_pay_amount": 5000,
            "comment": "规则14收款0金额阻断",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RULE14-RECEIPT-BLOCK",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200

    receipt_doc = _query_receipt_docs(sales_order_id=sales_order_id, doc_type="NORMAL")[
        0
    ]
    blocked_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/confirm",
        json={"amount_actual": 0, "voucher_files": []},
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RULE14-RECEIPT-BLOCK-CONFIRM",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert blocked_response.status_code == 200
    assert blocked_response.json()["status"] == "待补录金额"
    refreshed_doc = _query_receipt_docs(
        sales_order_id=sales_order_id, doc_type="NORMAL"
    )[0]
    assert refreshed_doc.status == "待补录金额"


def test_zero_pay_exception_confirm_passes_rule11(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )
    approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 5000,
            "actual_pay_amount": 0,
            "comment": "规则11付款0金额放行",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RULE11-PAY",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200
    purchase_order_id = approve_response.json()["purchase_order_id"]

    payment_doc = _query_payment_docs(
        purchase_order_id=purchase_order_id, doc_type="NORMAL"
    )[0]
    confirm_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/confirm",
        json={"amount_actual": 0, "voucher_files": []},
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RULE11-PAY-CONFIRM",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["status"] == "已确认"
    assert body["voucher_required"] is False
    assert body["voucher_exempt_reason"] == "例外放行（需后补付款单）"


def test_zero_amount_deposit_payment_confirm_moves_to_pending_supplement(
    auth_headers,
) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    payment_doc = _query_payment_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]

    confirm_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/confirm",
        json={"amount_actual": 0, "voucher_files": []},
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-DEPOSIT-PAY-ZERO",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "待补录金额"
    refreshed_doc = _query_payment_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]
    assert refreshed_doc.status == "待补录金额"


def test_pending_supplement_receipt_can_be_confirmed_after_amount_is_backfilled(
    auth_headers,
) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    sales_order_id = _create_sales_order_in_pending_finance(
        auth_headers, sales_contract_id=sales_contract_id
    )
    approve_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/finance-approve",
        json={
            "result": True,
            "purchase_contract_id": purchase_contract_id,
            "actual_receipt_amount": 0,
            "actual_pay_amount": 6000,
            "comment": "先转待补录后再补录金额",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RECEIPT-REFILL-1",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200

    receipt_doc = _query_receipt_docs(sales_order_id=sales_order_id, doc_type="NORMAL")[
        0
    ]
    blocked_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/confirm",
        json={"amount_actual": 0, "voucher_files": []},
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RECEIPT-REFILL-2",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert blocked_response.status_code == 200
    assert blocked_response.json()["status"] == "待补录金额"

    refill_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/confirm",
        json={
            "amount_actual": 8800.45,
            "voucher_files": ["CODEX-TEST-/receipt-backfill-001.png"],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-FINANCE-RECEIPT-REFILL-3",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert refill_response.status_code == 200
    body = refill_response.json()
    assert body["status"] == "已确认"
    assert body["voucher_file_paths"] == ["CODEX-TEST-/receipt-backfill-001.png"]
    refreshed_doc = _query_receipt_docs(
        sales_order_id=sales_order_id, doc_type="NORMAL"
    )[0]
    assert refreshed_doc.amount_actual == Decimal("8800.45")
    assert refreshed_doc.status == "已确认"


def test_payment_doc_refund_review_and_writeoff_flow(auth_headers) -> None:
    contract_id = _create_effective_purchase_contract(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    payment_doc = _query_payment_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]

    confirm_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/confirm",
        json={
            "amount_actual": 3200.55,
            "voucher_files": ["CODEX-TEST-/m8-refund-payment-confirm.png"],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M8-PAY-REFUND-CONFIRM",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert confirm_response.status_code == 200

    request_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/refund-request",
        json={"refund_amount": 1000.00, "reason": "CODEX-TEST-付款退款申请"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-PAY-REFUND-REQUEST-1",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert request_response.status_code == 200
    assert request_response.json()["refund_status"] == "待审核"

    reject_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/refund-reject",
        json={"reason": "CODEX-TEST-付款退款驳回"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-PAY-REFUND-REJECT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert reject_response.status_code == 200
    reject_body = reject_response.json()
    assert reject_body["refund_status"] == "驳回"
    assert Decimal(str(reject_body["refund_amount"])) == Decimal("0.00")

    request_response_2 = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/refund-request",
        json={"refund_amount": 1000.00, "reason": "CODEX-TEST-付款退款复提"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-PAY-REFUND-REQUEST-2",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert request_response_2.status_code == 200
    assert request_response_2.json()["refund_status"] == "待审核"

    approve_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/refund-approve",
        json={"reason": "CODEX-TEST-付款退款审核通过"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-PAY-REFUND-APPROVE",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["refund_status"] == "部分退款"

    writeoff_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/writeoff",
        json={"comment": "CODEX-TEST-付款核销"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-PAY-WRITEOFF",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert writeoff_response.status_code == 200
    assert writeoff_response.json()["status"] == "已核销"


def test_receipt_doc_refund_review_reject_and_writeoff_guard(auth_headers) -> None:
    contract_id = _create_effective_sales_contract(
        auth_headers, customer_id=CUSTOMER_COMPANY_ID
    )
    receipt_doc = _query_receipt_docs(contract_id=contract_id, doc_type="DEPOSIT")[0]

    blocked_request_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/refund-request",
        json={"refund_amount": 100.00, "reason": "CODEX-TEST-草稿收款退款申请"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-REC-REFUND-BLOCK",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert blocked_request_response.status_code == 409
    assert (
        blocked_request_response.json()["detail"] == "当前收款单状态不允许发起退款审核"
    )

    confirm_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/confirm",
        json={
            "amount_actual": 5000.00,
            "voucher_files": ["CODEX-TEST-/m8-refund-receipt-confirm.png"],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M8-REC-REFUND-CONFIRM",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert confirm_response.status_code == 200

    writeoff_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/writeoff",
        json={"comment": "CODEX-TEST-收款核销"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-REC-WRITEOFF",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert writeoff_response.status_code == 200
    assert writeoff_response.json()["status"] == "已核销"

    request_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/refund-request",
        json={"refund_amount": 5000.00, "reason": "CODEX-TEST-收款退款申请"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-REC-REFUND-REQUEST",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert request_response.status_code == 200
    assert request_response.json()["refund_status"] == "待审核"

    reject_response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc.id}/refund-reject",
        json={"reason": "CODEX-TEST-收款退款驳回"},
        headers=auth_headers(
            user_id="CODEX-TEST-M8-REC-REFUND-REJECT",
            role_code="finance",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert reject_response.status_code == 200
    reject_body = reject_response.json()
    assert reject_body["refund_status"] == "驳回"
    assert Decimal(str(reject_body["refund_amount"])) == Decimal("0.00")


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


def _query_doc_attachments(
    owner_doc_type: str, owner_doc_id: int, biz_tag: str
) -> list[str]:
    with SessionLocal() as db:
        statement = (
            select(DocAttachment.path)
            .where(
                DocAttachment.owner_doc_type == owner_doc_type,
                DocAttachment.owner_doc_id == owner_doc_id,
                DocAttachment.biz_tag == biz_tag,
            )
            .order_by(DocAttachment.id)
        )
        return list(db.scalars(statement).all())


def _query_contract_tasks(*, contract_id: int) -> list[ContractEffectiveTask]:
    with SessionLocal() as db:
        statement = (
            select(ContractEffectiveTask)
            .where(ContractEffectiveTask.contract_id == contract_id)
            .order_by(ContractEffectiveTask.id)
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


def _create_effective_sales_contract(
    auth_headers,
    *,
    customer_id: str,
    qty_signed: Decimal = Decimal("300.000"),
    unit_price: Decimal = Decimal("6500.25"),
) -> int:
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": f"CODEX-TEST-M4-SALES-{uuid4().hex[:10]}",
            "customer_id": customer_id,
            "items": [
                {
                    "oil_product_id": "OIL-92",
                    "qty_signed": float(qty_signed),
                    "unit_price": float(unit_price),
                }
            ],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M4-FINANCE-CREATE-SALES-CONTRACT",
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
        json={"comment": "M4销售合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M4销售合同生效"},
        headers=auth_headers(),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_effective_purchase_contract(
    auth_headers,
    *,
    supplier_id: str,
    qty_signed: Decimal = Decimal("400.000"),
    unit_price: Decimal = Decimal("6300.80"),
) -> int:
    create_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": f"CODEX-TEST-M4-PURCHASE-{uuid4().hex[:10]}",
            "supplier_id": supplier_id,
            "items": [
                {
                    "oil_product_id": "OIL-92",
                    "qty_signed": float(qty_signed),
                    "unit_price": float(unit_price),
                }
            ],
        },
        headers=auth_headers(
            user_id="CODEX-TEST-M4-FINANCE-CREATE-PURCHASE-CONTRACT",
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
        json={"comment": "M4采购合同提交"},
        headers=auth_headers(),
    )
    assert submit_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M4采购合同生效"},
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
            user_id="CODEX-TEST-M4-CUSTOMER-CREATE-ORDER",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_sales_order_in_pending_finance(
    auth_headers, *, sales_contract_id: int
) -> int:
    sales_order_id = _create_sales_order_draft(
        auth_headers, sales_contract_id=sales_contract_id
    )
    submit_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/submit",
        json={"comment": "M4自动化提交"},
        headers=auth_headers(
            user_id="CODEX-TEST-M4-CUSTOMER-SUBMIT",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert submit_response.status_code == 200

    ops_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "M4运营审批通过"},
        headers=auth_headers(
            user_id="CODEX-TEST-M4-OPS-APPROVE",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )
    assert ops_response.status_code == 200
    return sales_order_id
