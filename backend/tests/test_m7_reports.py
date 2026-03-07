from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.contract import Contract
from app.models.inbound_doc import InboundDoc
from app.models.outbound_doc import OutboundDoc
from app.models.payment_doc import PaymentDoc
from app.models.receipt_doc import ReceiptDoc
from app.models.report_snapshot import ReportSnapshot

client = TestClient(app)

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
CUSTOMER_COMPANY_ID = "CODEX-TEST-CUSTOMER-COMPANY"
SUPPLIER_COMPANY_ID = "CODEX-TEST-SUPPLIER-COMPANY"
WAREHOUSE_COMPANY_ID = "CODEX-TEST-WAREHOUSE-COMPANY"
RECEIPT_VOUCHER = ["CODEX-TEST-/receipt-voucher-m7.jpg"]
PAYMENT_VOUCHER = ["CODEX-TEST-/payment-voucher-m7.jpg"]


def test_dashboard_summary_requires_admin_web_operator_identity(auth_headers) -> None:
    response = client.get(
        "/api/v1/dashboard/summary",
        headers=auth_headers(
            user_id="CODEX-TEST-CUSTOMER-M7-DASH",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "当前角色无权访问该接口"


def test_dashboard_summary_matches_current_database_formula_and_persists_snapshot(
    auth_headers,
) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    sales_order_id, _ = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=sales_contract_id,
        purchase_contract_id=purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("600025.00"),
        actual_pay_amount=Decimal("580080.00"),
    )

    deposit_receipt_doc = _query_receipt_doc(
        contract_id=sales_contract_id, doc_type="DEPOSIT"
    )
    normal_receipt_doc = _query_receipt_doc(
        contract_id=sales_contract_id, sales_order_id=sales_order_id, doc_type="NORMAL"
    )
    deposit_payment_doc = _query_payment_doc(
        contract_id=purchase_contract_id, doc_type="DEPOSIT"
    )
    normal_payment_doc = _query_payment_doc(
        contract_id=purchase_contract_id,
        purchase_order_sales_order_id=sales_order_id,
        doc_type="NORMAL",
    )
    inbound_doc = _query_inbound_doc(contract_id=purchase_contract_id)

    _confirm_receipt_doc(auth_headers, deposit_receipt_doc.id, Decimal("50000.00"))
    _confirm_receipt_doc(auth_headers, normal_receipt_doc.id, Decimal("600025.00"))
    _confirm_payment_doc(auth_headers, deposit_payment_doc.id, Decimal("50000.00"))
    _confirm_payment_doc(auth_headers, normal_payment_doc.id, Decimal("580080.00"))
    _submit_inbound_doc(auth_headers, inbound_doc.id, Decimal("100.000"))
    outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=sales_contract_id,
        sales_order_id=sales_order_id,
        source_ticket_no=f"CODEX-TEST-M7-DASH-{uuid4().hex[:8]}",
        actual_qty=Decimal("100.000"),
    )
    _submit_outbound_doc(auth_headers, outbound_doc_id, Decimal("100.000"))

    response = client.get(
        "/api/v1/dashboard/summary",
        headers=auth_headers(
            user_id="CODEX-TEST-M7-DASH-READER",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="admin_web",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    expected = _compute_expected_dashboard_metrics()
    assert (
        Decimal(str(body["contract_execution_rate"]))
        == expected["contract_execution_rate"]
    )
    assert (
        Decimal(str(body["actual_receipt_today"])) == expected["actual_receipt_today"]
    )
    assert (
        Decimal(str(body["actual_payment_today"])) == expected["actual_payment_today"]
    )
    assert (
        Decimal(str(body["inventory_turnover_30d"]))
        == expected["inventory_turnover_30d"]
    )
    assert body["threshold_alert_count"] == expected["threshold_alert_count"]
    assert body["metric_version"] == "v1"
    assert body["sla_status"] == "正常"

    snapshot = _latest_report_snapshot("dashboard_summary")
    assert snapshot is not None
    assert snapshot.version == "v1"
    assert (
        Decimal(str(snapshot.metric_payload["contract_execution_rate"]))
        == expected["contract_execution_rate"]
    )


def test_board_tasks_returns_counts_and_contains_current_actionable_items(
    auth_headers,
) -> None:
    pending_sales_contract_id = _create_effective_sales_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    pending_purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    pending_sales_order_id, _ = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=pending_sales_contract_id,
        purchase_contract_id=pending_purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("0.00"),
        actual_pay_amount=Decimal("0.00"),
    )
    pending_receipt_doc = _query_receipt_doc(
        contract_id=pending_sales_contract_id,
        sales_order_id=pending_sales_order_id,
        doc_type="NORMAL",
    )
    pending_response = client.post(
        f"/api/v1/receipt-docs/{pending_receipt_doc.id}/confirm",
        json={"amount_actual": 0, "voucher_files": []},
        headers=_finance_headers(auth_headers, "CODEX-TEST-M7-PENDING-RECEIPT"),
    )
    assert pending_response.status_code == 200
    assert pending_response.json()["status"] == "待补录金额"

    validation_purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    validation_inbound_doc = _query_inbound_doc(
        contract_id=validation_purchase_contract_id
    )
    validation_response = client.post(
        f"/api/v1/inbound-docs/{validation_inbound_doc.id}/submit",
        json={"actual_qty": 106, "warehouse_id": "CODEX-TEST-WH-M7-001"},
        headers=_warehouse_headers(auth_headers, "CODEX-TEST-M7-WH-VALIDATION"),
    )
    assert validation_response.status_code == 200
    assert validation_response.json()["status"] == "校验失败"

    qty_done_sales_contract_id = _create_effective_sales_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    qty_done_purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    qty_done_sales_order_id, _ = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=qty_done_sales_contract_id,
        purchase_contract_id=qty_done_purchase_contract_id,
        qty=Decimal("100.000"),
        actual_receipt_amount=Decimal("500000.00"),
        actual_pay_amount=Decimal("0.00"),
    )
    qty_done_deposit_doc = _query_receipt_doc(
        contract_id=qty_done_sales_contract_id, doc_type="DEPOSIT"
    )
    qty_done_normal_doc = _query_receipt_doc(
        contract_id=qty_done_sales_contract_id,
        sales_order_id=qty_done_sales_order_id,
        doc_type="NORMAL",
    )
    _confirm_receipt_doc(auth_headers, qty_done_deposit_doc.id, Decimal("50000.00"))
    _confirm_receipt_doc(auth_headers, qty_done_normal_doc.id, Decimal("500000.00"))
    qty_done_outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=qty_done_sales_contract_id,
        sales_order_id=qty_done_sales_order_id,
        source_ticket_no=f"CODEX-TEST-M7-QTYDONE-{uuid4().hex[:8]}",
        actual_qty=Decimal("100.000"),
    )
    _submit_outbound_doc(auth_headers, qty_done_outbound_doc_id, Decimal("100.000"))

    response = client.get(
        "/api/v1/boards/tasks",
        headers=_ops_admin_web_headers(auth_headers, "CODEX-TEST-M7-BOARD-READER"),
    )

    assert response.status_code == 200
    body = response.json()
    expected = _compute_expected_board_metrics()
    assert body["pending_supplement_count"] == expected["pending_supplement_count"]
    assert body["validation_failed_count"] == expected["validation_failed_count"]
    assert body["qty_done_not_closed_count"] == expected["qty_done_not_closed_count"]
    assert any(
        item["biz_id"] == pending_receipt_doc.id
        for item in body["pending_supplement_items"]
    )
    assert any(
        item["biz_id"] == validation_inbound_doc.id
        for item in body["validation_failed_items"]
    )
    assert any(
        item["biz_id"] == qty_done_sales_contract_id
        for item in body["qty_done_not_closed_items"]
    )

    snapshot = _latest_report_snapshot("board_tasks")
    assert snapshot is not None
    assert snapshot.version == "v1"


def test_light_overview_blocks_non_operator_roles_and_matches_current_formula(
    auth_headers,
) -> None:
    blocked_response = client.get(
        "/api/v1/reports/light/overview",
        headers=auth_headers(
            user_id="CODEX-TEST-M7-LIGHT-CUSTOMER",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert blocked_response.status_code == 403
    assert blocked_response.json()["detail"] == "当前角色无权访问该接口"

    response = client.get(
        "/api/v1/reports/light/overview",
        headers=auth_headers(
            user_id="CODEX-TEST-M7-LIGHT-OPS",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="miniprogram",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    expected = _compute_expected_light_metrics()
    assert (
        Decimal(str(body["actual_receipt_today"])) == expected["actual_receipt_today"]
    )
    assert (
        Decimal(str(body["actual_payment_today"])) == expected["actual_payment_today"]
    )
    assert Decimal(str(body["inbound_qty_today"])) == expected["inbound_qty_today"]
    assert Decimal(str(body["outbound_qty_today"])) == expected["outbound_qty_today"]
    assert body["abnormal_count"] == expected["abnormal_count"]
    assert body["pending_supplement_count"] == expected["pending_supplement_count"]
    assert body["validation_failed_count"] == expected["validation_failed_count"]
    assert body["qty_done_not_closed_count"] == expected["qty_done_not_closed_count"]

    snapshot = _latest_report_snapshot("light_overview")
    assert snapshot is not None
    assert snapshot.version == "v1"


def test_admin_multi_dim_report_and_export_support_filters(auth_headers) -> None:
    sales_contract_id = _create_effective_sales_contract(
        auth_headers,
        qty_signed=Decimal("50.000"),
    )
    purchase_contract_id = _create_effective_purchase_contract(
        auth_headers,
        qty_signed=Decimal("50.000"),
    )

    receipt_doc = _query_receipt_doc(contract_id=sales_contract_id, doc_type="DEPOSIT")
    payment_doc = _query_payment_doc(
        contract_id=purchase_contract_id,
        doc_type="DEPOSIT",
    )
    _confirm_receipt_doc(auth_headers, receipt_doc.id, Decimal("15000.00"))
    _confirm_payment_doc(auth_headers, payment_doc.id, Decimal("12000.00"))

    refund_request_response = client.post(
        f"/api/v1/payment-docs/{payment_doc.id}/refund-request",
        json={
            "refund_amount": 1000.00,
            "reason": "CODEX-TEST-M8-21-多维报表退款申请",
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-21-REFUND-REQUEST"),
    )
    assert refund_request_response.status_code == 200

    response = client.get(
        "/api/v1/reports/admin/multi-dim",
        params={"group_by": "contract_direction"},
        headers=_ops_admin_web_headers(auth_headers, "CODEX-TEST-M8-21-MULTI-DIM"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["group_by"] == "contract_direction"
    assert body["metric_version"] == "v1"
    assert body["message"] == "后台多维报表查询成功"
    assert any(row["dimension_value"] == "销售" for row in body["rows"])
    assert any(row["dimension_value"] == "采购" for row in body["rows"])

    purchase_row = next(row for row in body["rows"] if row["dimension_value"] == "采购")
    assert purchase_row["refund_pending_review_count"] >= 1
    assert Decimal(str(body["total_payment_net_amount"])) >= Decimal("11000.00")

    filtered_response = client.get(
        "/api/v1/reports/admin/multi-dim",
        params={
            "group_by": "refund_status",
            "contract_direction": "purchase",
            "date_from": date.today().isoformat(),
            "date_to": date.today().isoformat(),
        },
        headers=_ops_admin_web_headers(
            auth_headers, "CODEX-TEST-M8-21-MULTI-DIM-FILTER"
        ),
    )
    assert filtered_response.status_code == 200
    filtered_body = filtered_response.json()
    assert any(row["dimension_value"] == "待审核" for row in filtered_body["rows"])

    blocked_export_response = client.get(
        "/api/v1/reports/admin/multi-dim/export",
        params={"group_by": "refund_status", "contract_direction": "purchase"},
        headers=_ops_admin_web_headers(
            auth_headers, "CODEX-TEST-M8-21-MULTI-DIM-EXPORT"
        ),
    )
    assert blocked_export_response.status_code == 403
    assert blocked_export_response.json()["detail"] == "当前角色无权访问该接口"

    export_response = client.get(
        "/api/v1/reports/admin/multi-dim/export",
        params={"group_by": "refund_status", "contract_direction": "purchase"},
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-23-MULTI-DIM-EXPORT"),
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert (
        'attachment; filename="multi-dim-report-'
        in export_response.headers["content-disposition"]
    )
    assert "维度,维度值,收款净额,付款净额,资金净流入" in export_response.text
    assert "待审核" in export_response.text


def test_report_metric_version_must_exist(auth_headers) -> None:
    response = client.get(
        "/api/v1/dashboard/summary",
        params={"metric_version": "v999"},
        headers=_ops_admin_web_headers(auth_headers, "CODEX-TEST-M7-VERSION-BLOCK"),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "当前报表口径版本不存在"


def _compute_expected_dashboard_metrics() -> dict[str, Decimal | int]:
    db = SessionLocal()
    try:
        contracts = db.scalars(select(Contract)).all()
        total_signed = Decimal("0.000")
        total_done = Decimal("0.000")
        for contract in contracts:
            if contract.status not in {
                "生效中",
                "数量履约完成",
                "已关闭",
                "手工关闭",
                "已归档",
            }:
                continue
            contract_with_items = db.get(Contract, contract.id)
            assert contract_with_items is not None
            for item in contract_with_items.items:
                signed_qty = Decimal(str(item.qty_signed))
                done_qty = Decimal(
                    str(
                        item.qty_in_acc
                        if contract.direction == "purchase"
                        else item.qty_out_acc
                    )
                )
                total_signed += signed_qty
                total_done += min(done_qty, signed_qty)
        contract_execution_rate = (
            Decimal("0.000000")
            if total_signed <= Decimal("0.000")
            else (total_done / total_signed).quantize(Decimal("0.000001"))
        )

        start_utc, end_utc = _today_window_utc()
        actual_receipt_today = Decimal("0.00")
        for doc in db.scalars(
            select(ReceiptDoc).where(ReceiptDoc.status.in_(["已确认", "已核销"]))
        ).all():
            if (
                doc.confirmed_at
                and start_utc <= doc.confirmed_at.astimezone(UTC) < end_utc
            ):
                actual_receipt_today += Decimal(str(doc.amount_actual)) - Decimal(
                    str(doc.refund_amount)
                )
        actual_receipt_today = actual_receipt_today.quantize(Decimal("0.01"))

        actual_payment_today = Decimal("0.00")
        for doc in db.scalars(
            select(PaymentDoc).where(PaymentDoc.status.in_(["已确认", "已核销"]))
        ).all():
            if (
                doc.confirmed_at
                and start_utc <= doc.confirmed_at.astimezone(UTC) < end_utc
            ):
                actual_payment_today += Decimal(str(doc.amount_actual)) - Decimal(
                    str(doc.refund_amount)
                )
        actual_payment_today = actual_payment_today.quantize(Decimal("0.01"))

        recent_start, recent_end = _recent_30_day_window_utc()
        current_available_stock = Decimal("0.000")
        recent_outbound = Decimal("0.000")
        for doc in db.scalars(
            select(InboundDoc).where(InboundDoc.status == "已过账")
        ).all():
            current_available_stock += Decimal(str(doc.actual_qty))
        for doc in db.scalars(
            select(OutboundDoc).where(OutboundDoc.status == "已过账")
        ).all():
            qty = Decimal(str(doc.actual_qty))
            current_available_stock -= qty
            if (
                doc.submitted_at
                and recent_start <= doc.submitted_at.astimezone(UTC) < recent_end
            ):
                recent_outbound += qty
        inventory_turnover_30d = Decimal("0.000000")
        if current_available_stock > Decimal("0.000"):
            inventory_turnover_30d = (
                recent_outbound / current_available_stock
            ).quantize(Decimal("0.000001"))

        threshold_alert_count = _compute_expected_board_metrics()["total_alert_count"]
        return {
            "contract_execution_rate": contract_execution_rate,
            "actual_receipt_today": actual_receipt_today,
            "actual_payment_today": actual_payment_today,
            "inventory_turnover_30d": inventory_turnover_30d,
            "threshold_alert_count": threshold_alert_count,
        }
    finally:
        db.close()


def _compute_expected_board_metrics() -> dict[str, int]:
    db = SessionLocal()
    try:
        pending_supplement_count = len(
            db.scalars(
                select(ReceiptDoc).where(ReceiptDoc.status == "待补录金额")
            ).all()
        ) + len(
            db.scalars(
                select(PaymentDoc).where(PaymentDoc.status == "待补录金额")
            ).all()
        )
        validation_failed_count = len(
            db.scalars(select(InboundDoc).where(InboundDoc.status == "校验失败")).all()
        ) + len(
            db.scalars(
                select(OutboundDoc).where(OutboundDoc.status == "校验失败")
            ).all()
        )
        qty_done_not_closed_count = len(
            db.scalars(select(Contract).where(Contract.status == "数量履约完成")).all()
        )
        return {
            "pending_supplement_count": pending_supplement_count,
            "validation_failed_count": validation_failed_count,
            "qty_done_not_closed_count": qty_done_not_closed_count,
            "total_alert_count": pending_supplement_count
            + validation_failed_count
            + qty_done_not_closed_count,
        }
    finally:
        db.close()


def _compute_expected_light_metrics() -> dict[str, Decimal | int]:
    dashboard_metrics = _compute_expected_dashboard_metrics()
    board_metrics = _compute_expected_board_metrics()
    db = SessionLocal()
    try:
        start_utc, end_utc = _today_window_utc()
        inbound_qty_today = Decimal("0.000")
        for doc in db.scalars(
            select(InboundDoc).where(InboundDoc.status == "已过账")
        ).all():
            if (
                doc.submitted_at
                and start_utc <= doc.submitted_at.astimezone(UTC) < end_utc
            ):
                inbound_qty_today += Decimal(str(doc.actual_qty))
        outbound_qty_today = Decimal("0.000")
        for doc in db.scalars(
            select(OutboundDoc).where(OutboundDoc.status == "已过账")
        ).all():
            if (
                doc.submitted_at
                and start_utc <= doc.submitted_at.astimezone(UTC) < end_utc
            ):
                outbound_qty_today += Decimal(str(doc.actual_qty))
        return {
            "actual_receipt_today": dashboard_metrics["actual_receipt_today"],
            "actual_payment_today": dashboard_metrics["actual_payment_today"],
            "inbound_qty_today": inbound_qty_today.quantize(Decimal("0.001")),
            "outbound_qty_today": outbound_qty_today.quantize(Decimal("0.001")),
            "abnormal_count": board_metrics["total_alert_count"],
            "pending_supplement_count": board_metrics["pending_supplement_count"],
            "validation_failed_count": board_metrics["validation_failed_count"],
            "qty_done_not_closed_count": board_metrics["qty_done_not_closed_count"],
        }
    finally:
        db.close()


def _create_effective_sales_contract(
    auth_headers,
    *,
    qty_signed: Decimal,
    unit_price: Decimal = Decimal("6000.25"),
    customer_id: str = CUSTOMER_COMPANY_ID,
) -> int:
    contract_no = f"CODEX-TEST-M7-SC-{uuid4().hex[:10]}"
    create_response = client.post(
        "/api/v1/contracts/sales",
        json={
            "contract_no": contract_no,
            "customer_id": customer_id,
            "items": [
                {
                    "oil_product_id": "OIL-92",
                    "qty_signed": float(qty_signed),
                    "unit_price": float(unit_price),
                }
            ],
        },
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-SC-{uuid4().hex[:6]}"
        ),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]
    submit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "M7 合同提交流程"},
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-SC-SUB-{uuid4().hex[:6]}"
        ),
    )
    assert submit_response.status_code == 200
    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M7 销售合同生效"},
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-SC-APP-{uuid4().hex[:6]}"
        ),
    )
    assert approve_response.status_code == 200
    return contract_id


def _create_effective_purchase_contract(
    auth_headers,
    *,
    qty_signed: Decimal,
    unit_price: Decimal = Decimal("5800.80"),
    supplier_id: str = SUPPLIER_COMPANY_ID,
) -> int:
    contract_no = f"CODEX-TEST-M7-PC-{uuid4().hex[:10]}"
    create_response = client.post(
        "/api/v1/contracts/purchase",
        json={
            "contract_no": contract_no,
            "supplier_id": supplier_id,
            "items": [
                {
                    "oil_product_id": "OIL-92",
                    "qty_signed": float(qty_signed),
                    "unit_price": float(unit_price),
                }
            ],
        },
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-PC-{uuid4().hex[:6]}"
        ),
    )
    assert create_response.status_code == 200
    contract_id = create_response.json()["id"]
    submit_response = client.post(
        f"/api/v1/contracts/{contract_id}/submit",
        json={"comment": "M7 采购合同提交流程"},
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-PC-SUB-{uuid4().hex[:6]}"
        ),
    )
    assert submit_response.status_code == 200
    approve_response = client.post(
        f"/api/v1/contracts/{contract_id}/approve",
        json={"approval_result": True, "comment": "M7 采购合同生效"},
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-PC-APP-{uuid4().hex[:6]}"
        ),
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
) -> tuple[int, int]:
    create_response = client.post(
        "/api/v1/sales-orders",
        json={
            "sales_contract_id": sales_contract_id,
            "oil_product_id": "OIL-92",
            "qty": float(qty),
            "unit_price": 6000.25,
        },
        headers=auth_headers(
            user_id=f"CODEX-TEST-M7-CUSTOMER-{uuid4().hex[:6]}",
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
        json={"comment": "M7 销售订单提交"},
        headers=auth_headers(
            user_id=f"CODEX-TEST-M7-CUSTOMER-SUB-{uuid4().hex[:6]}",
            role_code="customer",
            company_id=CUSTOMER_COMPANY_ID,
            company_type="customer_company",
            client_type="miniprogram",
        ),
    )
    assert submit_response.status_code == 200

    ops_response = client.post(
        f"/api/v1/sales-orders/{sales_order_id}/ops-approve",
        json={"result": True, "comment": "M7 运营审批通过"},
        headers=_ops_admin_web_headers(
            auth_headers, f"CODEX-TEST-M7-OPS-{uuid4().hex[:6]}"
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
            "comment": "M7 财务审批通过",
        },
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-ORDER-{uuid4().hex[:6]}"
        ),
    )
    assert finance_response.status_code == 200
    return sales_order_id, finance_response.json()["purchase_order_id"]


def _confirm_receipt_doc(
    auth_headers, receipt_doc_id: int, amount_actual: Decimal
) -> None:
    response = client.post(
        f"/api/v1/receipt-docs/{receipt_doc_id}/confirm",
        json={
            "amount_actual": float(amount_actual),
            "voucher_files": RECEIPT_VOUCHER if amount_actual > Decimal("0.00") else [],
        },
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-RECEIPT-{uuid4().hex[:6]}"
        ),
    )
    assert response.status_code == 200


def _confirm_payment_doc(
    auth_headers, payment_doc_id: int, amount_actual: Decimal
) -> None:
    response = client.post(
        f"/api/v1/payment-docs/{payment_doc_id}/confirm",
        json={
            "amount_actual": float(amount_actual),
            "voucher_files": PAYMENT_VOUCHER if amount_actual > Decimal("0.00") else [],
        },
        headers=_finance_headers(
            auth_headers, f"CODEX-TEST-M7-FINANCE-PAY-{uuid4().hex[:6]}"
        ),
    )
    assert response.status_code == 200


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
            "warehouse_id": "CODEX-TEST-WH-M7-001",
        },
        headers=_warehouse_headers(
            auth_headers, f"CODEX-TEST-M7-WH-CREATE-{uuid4().hex[:6]}"
        ),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _submit_outbound_doc(
    auth_headers, outbound_doc_id: int, actual_qty: Decimal
) -> None:
    response = client.post(
        f"/api/v1/outbound-docs/{outbound_doc_id}/submit",
        json={"actual_qty": float(actual_qty), "warehouse_id": "CODEX-TEST-WH-M7-001"},
        headers=_warehouse_headers(
            auth_headers, f"CODEX-TEST-M7-WH-SUB-OUT-{uuid4().hex[:6]}"
        ),
    )
    assert response.status_code == 200


def _submit_inbound_doc(auth_headers, inbound_doc_id: int, actual_qty: Decimal) -> None:
    response = client.post(
        f"/api/v1/inbound-docs/{inbound_doc_id}/submit",
        json={"actual_qty": float(actual_qty), "warehouse_id": "CODEX-TEST-WH-M7-001"},
        headers=_warehouse_headers(
            auth_headers, f"CODEX-TEST-M7-WH-SUB-IN-{uuid4().hex[:6]}"
        ),
    )
    assert response.status_code == 200


def _query_receipt_doc(
    *,
    contract_id: int,
    doc_type: str,
    sales_order_id: int | None = None,
) -> ReceiptDoc:
    db = SessionLocal()
    try:
        statement = select(ReceiptDoc).where(
            ReceiptDoc.contract_id == contract_id, ReceiptDoc.doc_type == doc_type
        )
        if sales_order_id is None:
            statement = statement.where(ReceiptDoc.sales_order_id.is_(None))
        else:
            statement = statement.where(ReceiptDoc.sales_order_id == sales_order_id)
        doc = db.scalar(statement.order_by(ReceiptDoc.id.desc()).limit(1))
        assert doc is not None
        return doc
    finally:
        db.close()


def _query_payment_doc(
    *,
    contract_id: int,
    doc_type: str,
    purchase_order_sales_order_id: int | None = None,
) -> PaymentDoc:
    db = SessionLocal()
    try:
        statement = select(PaymentDoc).where(
            PaymentDoc.contract_id == contract_id, PaymentDoc.doc_type == doc_type
        )
        docs = db.scalars(statement.order_by(PaymentDoc.id.desc())).all()
        if purchase_order_sales_order_id is None:
            for doc in docs:
                if doc.purchase_order_id is None:
                    return doc
        else:
            for doc in docs:
                if (
                    doc.purchase_order
                    and doc.purchase_order.source_sales_order_id
                    == purchase_order_sales_order_id
                ):
                    return doc
        raise AssertionError("未找到目标付款单")
    finally:
        db.close()


def _query_inbound_doc(*, contract_id: int) -> InboundDoc:
    db = SessionLocal()
    try:
        doc = db.scalar(
            select(InboundDoc)
            .where(InboundDoc.contract_id == contract_id)
            .order_by(InboundDoc.id.desc())
            .limit(1)
        )
        assert doc is not None
        return doc
    finally:
        db.close()


def _latest_report_snapshot(report_code: str) -> ReportSnapshot | None:
    db = SessionLocal()
    try:
        return db.scalar(
            select(ReportSnapshot)
            .where(ReportSnapshot.report_code == report_code)
            .order_by(ReportSnapshot.snapshot_time.desc(), ReportSnapshot.id.desc())
            .limit(1)
        )
    finally:
        db.close()


def _finance_headers(auth_headers, user_id: str) -> dict[str, str]:
    return auth_headers(
        user_id=user_id,
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )


def _ops_admin_web_headers(auth_headers, user_id: str) -> dict[str, str]:
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
        company_id=WAREHOUSE_COMPANY_ID,
        company_type="warehouse_company",
        client_type="miniprogram",
    )


def _today_window_utc() -> tuple[datetime, datetime]:
    today_cn = datetime.now(SHANGHAI_TZ).date()
    start_local = datetime.combine(today_cn, time.min, tzinfo=SHANGHAI_TZ)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def _recent_30_day_window_utc() -> tuple[datetime, datetime]:
    today_cn = datetime.now(SHANGHAI_TZ).date()
    start_day = today_cn - timedelta(days=29)
    start_local = datetime.combine(start_day, time.min, tzinfo=SHANGHAI_TZ)
    end_local = datetime.combine(
        today_cn + timedelta(days=1), time.min, tzinfo=SHANGHAI_TZ
    )
    return start_local.astimezone(UTC), end_local.astimezone(UTC)
