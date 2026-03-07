from __future__ import annotations

from fastapi.testclient import TestClient
from uuid import uuid4

from app.db.session import SessionLocal
from app.main import app
from app.models.doc_attachment import DocAttachment

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
    assert body["status"] == "待供应商确认"
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


def test_supplier_can_confirm_delivery_for_own_purchase_order(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/confirm-delivery",
        json={"comment": "CODEX-TEST-已核对发货准备并完成确认"},
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-CONFIRM",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "供应商已确认"
    assert body["supplier_confirm_comment"] == "CODEX-TEST-已核对发货准备并完成确认"
    assert body["supplier_confirmed_at"] is not None


def test_supplier_confirm_delivery_respects_company_scope(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/confirm-delivery",
        json={"comment": "CODEX-TEST-跨公司确认阻断"},
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-CONFIRM-BLOCK",
            role_code="supplier",
            company_id="CODEX-TEST-SUPPLIER-OTHER-COMPANY",
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "当前供应商无权查看该采购订单"


def test_supplier_confirm_delivery_blocks_invalid_status(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    headers = auth_headers(
        user_id="CODEX-TEST-MINI-SUPPLIER-CONFIRM-STATUS",
        role_code="supplier",
        company_id=SUPPLIER_COMPANY_ID,
        company_type="supplier_company",
        client_type="miniprogram",
    )
    first_response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/confirm-delivery",
        json={"comment": "CODEX-TEST-首次确认"},
        headers=headers,
    )
    second_response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/confirm-delivery",
        json={"comment": "CODEX-TEST-重复确认"},
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "当前采购订单状态不允许提交发货确认"


def test_supplier_confirm_delivery_blocks_empty_comment(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/confirm-delivery",
        json={"comment": "   "},
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-CONFIRM-EMPTY",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "发货确认说明不能为空"


def test_supplier_can_upload_and_list_purchase_order_attachments(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    create_response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/attachments",
        json={
            "biz_tag": "SUPPLIER_STAMPED_DOC",
            "file_path": "CODEX-TEST-/supplier-stamped-doc-001.pdf",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-UPLOAD",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert create_response.status_code == 200
    create_body = create_response.json()
    assert create_body["biz_tag"] == "SUPPLIER_STAMPED_DOC"
    assert create_body["file_path"] == "CODEX-TEST-/supplier-stamped-doc-001.pdf"

    list_response = client.get(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/attachments",
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-UPLOAD-LIST",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["total"] == 1
    assert list_body["items"][0]["biz_tag"] == "SUPPLIER_STAMPED_DOC"
    assert (
        list_body["items"][0]["file_path"] == "CODEX-TEST-/supplier-stamped-doc-001.pdf"
    )
    assert _query_doc_attachments(purchase_order_id) == [
        ("SUPPLIER_STAMPED_DOC", "CODEX-TEST-/supplier-stamped-doc-001.pdf")
    ]


def test_supplier_attachment_upload_respects_company_scope(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/attachments",
        json={
            "biz_tag": "SUPPLIER_STAMPED_DOC",
            "file_path": "CODEX-TEST-/supplier-stamped-doc-002.pdf",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-UPLOAD-BLOCK",
            role_code="supplier",
            company_id="CODEX-TEST-SUPPLIER-OTHER-COMPANY",
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "当前供应商无权查看该采购订单"


def test_supplier_attachment_upload_blocks_invalid_biz_tag(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/attachments",
        json={
            "biz_tag": "PAYMENT_VOUCHER",
            "file_path": "CODEX-TEST-/supplier-invalid-tag.pdf",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-UPLOAD-TAG",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "当前附件业务标签不在首批开放范围内"


def test_supplier_attachment_upload_blocks_empty_file_path(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )

    response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/attachments",
        json={
            "biz_tag": "SUPPLIER_STAMPED_DOC",
            "file_path": "   ",
        },
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-UPLOAD-EMPTY",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "附件路径不能为空"


def test_supplier_attachment_upload_blocks_overlong_file_path(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    overlong_path = "CODEX-TEST-/" + ("a" * 600) + ".pdf"

    response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/attachments",
        json={
            "biz_tag": "SUPPLIER_STAMPED_DOC",
            "file_path": overlong_path,
        },
        headers=auth_headers(
            user_id="CODEX-TEST-MINI-SUPPLIER-UPLOAD-LONG",
            role_code="supplier",
            company_id=SUPPLIER_COMPANY_ID,
            company_type="supplier_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "附件路径长度不能超过512个字符"


def test_supplier_attachment_upload_blocks_duplicate_path(auth_headers) -> None:
    purchase_order_id = _create_purchase_order(
        auth_headers, supplier_id=SUPPLIER_COMPANY_ID
    )
    headers = auth_headers(
        user_id="CODEX-TEST-MINI-SUPPLIER-UPLOAD-DUP",
        role_code="supplier",
        company_id=SUPPLIER_COMPANY_ID,
        company_type="supplier_company",
        client_type="miniprogram",
    )
    payload = {
        "biz_tag": "SUPPLIER_DELIVERY_RECEIPT",
        "file_path": "CODEX-TEST-/supplier-delivery-receipt-001.pdf",
    }

    first_response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/attachments",
        json=payload,
        headers=headers,
    )
    duplicate_response = client.post(
        f"/api/v1/supplier/purchase-orders/{purchase_order_id}/attachments",
        json=payload,
        headers=headers,
    )

    assert first_response.status_code == 200
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "当前附件已存在，请勿重复上传"


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


def _query_doc_attachments(purchase_order_id: int) -> list[tuple[str, str]]:
    with SessionLocal() as db:
        rows = (
            db.query(DocAttachment)
            .filter(
                DocAttachment.owner_doc_type == "purchase_order",
                DocAttachment.owner_doc_id == purchase_order_id,
            )
            .order_by(DocAttachment.id)
            .all()
        )
        return [(row.biz_tag, row.path) for row in rows]
