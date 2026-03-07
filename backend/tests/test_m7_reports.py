from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
import os
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routers import reports as reports_router
from app.core.auth_actor import AuthenticatedActor
from app.db.session import SessionLocal
from app.main import app
from app.models.business_audit_log import BusinessAuditLog
from app.models.contract import Contract
from app.models.contract_item import ContractItem
from app.models.contract_qty_effect import ContractQtyEffect
from app.models.inbound_doc import InboundDoc
from app.models.outbound_doc import OutboundDoc
from app.models.payment_doc import PaymentDoc
from app.models.report_recompute_task import ReportRecomputeTask
from app.models.receipt_doc import ReceiptDoc
from app.models.report_export_task import ReportExportTask
from app.models.report_snapshot import ReportSnapshot
from app.services.report_recompute_service import create_summary_report_recompute_task
from app.services.report_service import create_admin_multi_dim_export_task

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
    _clear_daily_scan_audit_logs()

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

    stagnant_sales_contract_id = _create_effective_sales_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    stagnant_purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    stagnant_sales_order_id, _ = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=stagnant_sales_contract_id,
        purchase_contract_id=stagnant_purchase_contract_id,
        qty=Decimal("50.000"),
        actual_receipt_amount=Decimal("0.00"),
        actual_pay_amount=Decimal("0.00"),
    )
    stagnant_outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=stagnant_sales_contract_id,
        sales_order_id=stagnant_sales_order_id,
        source_ticket_no=f"CODEX-TEST-M8-26-STAGNANT-{uuid4().hex[:8]}",
        actual_qty=Decimal("50.000"),
    )
    _submit_outbound_doc(auth_headers, stagnant_outbound_doc_id, Decimal("50.000"))
    _backdate_contract_qty_effect(contract_id=stagnant_sales_contract_id, days_ago=4)
    _clear_daily_scan_audit_logs()

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
    assert body["fulfillment_stagnant_count"] == expected["fulfillment_stagnant_count"]
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
    stagnant_item = next(
        item
        for item in body["fulfillment_stagnant_items"]
        if item["biz_id"] == stagnant_sales_contract_id
    )
    assert stagnant_item["scan_type"] == "履约滞留"
    assert stagnant_item["days_without_effect"] >= 4
    assert stagnant_item["last_effect_at"] is not None

    repeated_response = client.get(
        "/api/v1/boards/tasks",
        headers=_ops_admin_web_headers(auth_headers, "CODEX-TEST-M8-26-BOARD-READER"),
    )
    assert repeated_response.status_code == 200
    assert (
        _count_daily_scan_audit_logs(
            contract_id=qty_done_sales_contract_id,
            scan_type="qty_done_not_closed",
        )
        == 1
    )
    assert (
        _count_daily_scan_audit_logs(
            contract_id=stagnant_sales_contract_id,
            scan_type="fulfillment_stagnant",
        )
        == 1
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
    _clear_daily_scan_audit_logs()

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
    assert body["fulfillment_stagnant_count"] == expected["fulfillment_stagnant_count"]

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


def test_admin_multi_dim_export_task_center_supports_create_list_download_and_retry(
    auth_headers,
) -> None:
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
    _confirm_receipt_doc(auth_headers, receipt_doc.id, Decimal("16000.00"))
    _confirm_payment_doc(auth_headers, payment_doc.id, Decimal("12000.00"))

    create_response = client.post(
        "/api/v1/reports/admin/multi-dim/export-tasks",
        json={
            "group_by": "contract_direction",
            "contract_direction": "purchase",
            "date_from": date.today().isoformat(),
            "date_to": date.today().isoformat(),
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-24-EXPORT-CREATE"),
    )
    assert create_response.status_code == 202
    create_body = create_response.json()
    task_id = create_body["task"]["id"]
    assert create_body["message"] == "导出任务已创建，正在后台生成文件"

    blocked_create_response = client.post(
        "/api/v1/reports/admin/multi-dim/export-tasks",
        json={"group_by": "contract_direction"},
        headers=_ops_admin_web_headers(auth_headers, "CODEX-TEST-M8-24-EXPORT-BLOCKED"),
    )
    assert blocked_create_response.status_code == 403
    assert blocked_create_response.json()["detail"] == "当前角色无权访问该接口"

    list_response = client.get(
        "/api/v1/reports/admin/multi-dim/export-tasks",
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-24-EXPORT-LIST"),
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    task_row = next(item for item in list_body["items"] if item["id"] == task_id)
    assert task_row["status"] == "已完成"
    assert task_row["filters"]["contract_direction"] == "purchase"
    assert task_row["file_name"].endswith(".csv")

    download_response = client.get(
        f"/api/v1/reports/admin/multi-dim/export-tasks/{task_id}/download",
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-24-EXPORT-DOWNLOAD"),
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("text/csv")
    assert task_row["file_name"] in download_response.headers["content-disposition"]
    assert "维度,维度值,收款净额,付款净额,资金净流入" in download_response.text

    task_after_download = _get_report_export_task(task_id)
    assert task_after_download is not None
    assert task_after_download.download_count == 1
    assert task_after_download.file_path is not None

    export_file_path = _resolve_report_export_task_file_path(
        task_after_download.file_path
    )
    export_file_path.unlink()

    missing_download_response = client.get(
        f"/api/v1/reports/admin/multi-dim/export-tasks/{task_id}/download",
        headers=_finance_headers(
            auth_headers, "CODEX-TEST-M8-24-EXPORT-DOWNLOAD-MISSING"
        ),
    )
    assert missing_download_response.status_code == 409
    assert (
        missing_download_response.json()["detail"]
        == "导出文件不存在，请先重试生成后再下载"
    )

    retry_response = client.post(
        f"/api/v1/reports/admin/multi-dim/export-tasks/{task_id}/retry",
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-24-EXPORT-RETRY"),
    )
    assert retry_response.status_code == 202
    assert retry_response.json()["message"] == "导出任务已重新发起，正在后台生成文件"

    retried_task = _get_report_export_task(task_id)
    assert retried_task is not None
    assert retried_task.status == "已完成"
    assert retried_task.retry_count == 1
    assert retried_task.file_path is not None

    blocked_list_response = client.get(
        "/api/v1/reports/admin/multi-dim/export-tasks",
        headers=_ops_admin_web_headers(
            auth_headers, "CODEX-TEST-M8-24-EXPORT-LIST-BLOCKED"
        ),
    )
    assert blocked_list_response.status_code == 403


def test_admin_multi_dim_export_task_create_reuses_same_in_progress_task() -> None:
    actor = AuthenticatedActor(
        user_id="CODEX-TEST-M8-24-IDEMPOTENT",
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )
    db = SessionLocal()
    try:
        first_dispatch = create_admin_multi_dim_export_task(
            db,
            actor=actor,
            metric_version="v1",
            group_by="contract_direction",
            contract_direction="purchase",
            doc_status="已确认",
            refund_status=None,
            date_from=date.today(),
            date_to=date.today(),
        )
        second_dispatch = create_admin_multi_dim_export_task(
            db,
            actor=actor,
            metric_version="v1",
            group_by="contract_direction",
            contract_direction="purchase",
            doc_status="已确认",
            refund_status=None,
            date_from=date.today(),
            date_to=date.today(),
        )
        assert first_dispatch.should_enqueue is True
        assert second_dispatch.should_enqueue is False
        assert first_dispatch.task.id == second_dispatch.task.id
        matching_tasks = db.scalars(
            select(ReportExportTask).where(
                ReportExportTask.requested_by == actor.user_id,
                ReportExportTask.status == "待处理",
            )
        ).all()
        assert len(matching_tasks) == 1
    finally:
        db.close()


def test_admin_multi_dim_export_task_retry_blocks_pending_task(auth_headers) -> None:
    actor = AuthenticatedActor(
        user_id="CODEX-TEST-M8-24-PENDING-RETRY",
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )
    db = SessionLocal()
    try:
        pending_dispatch = create_admin_multi_dim_export_task(
            db,
            actor=actor,
            metric_version="v1",
            group_by="refund_status",
            contract_direction="sales",
            doc_status=None,
            refund_status="未退款",
            date_from=None,
            date_to=None,
        )
    finally:
        db.close()

    retry_response = client.post(
        f"/api/v1/reports/admin/multi-dim/export-tasks/{pending_dispatch.task.id}/retry",
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-24-PENDING-RETRY-API"),
    )
    assert retry_response.status_code == 409
    assert retry_response.json()["detail"] == "当前导出任务不支持重试"


def test_admin_multi_dim_export_task_route_reuses_pending_task_without_requeue(
    auth_headers,
    monkeypatch,
) -> None:
    actor = AuthenticatedActor(
        user_id="CODEX-TEST-M8-24-ROUTE-DEDUP",
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )
    db = SessionLocal()
    try:
        pending_dispatch = create_admin_multi_dim_export_task(
            db,
            actor=actor,
            metric_version="v1",
            group_by="contract_direction",
            contract_direction="purchase",
            doc_status="已确认",
            refund_status=None,
            date_from=date.today(),
            date_to=date.today(),
        )
    finally:
        db.close()

    executed_task_ids: list[int] = []

    def fake_execute(task_id: int) -> None:
        executed_task_ids.append(task_id)

    monkeypatch.setattr(
        reports_router, "execute_admin_multi_dim_export_task", fake_execute
    )

    duplicate_response = client.post(
        "/api/v1/reports/admin/multi-dim/export-tasks",
        json={
            "group_by": "contract_direction",
            "contract_direction": "purchase",
            "doc_status": "已确认",
            "date_from": date.today().isoformat(),
            "date_to": date.today().isoformat(),
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-24-ROUTE-DEDUP"),
    )
    assert duplicate_response.status_code == 202
    assert duplicate_response.json()["task"]["id"] == pending_dispatch.task.id
    assert executed_task_ids == []


def test_summary_report_recompute_task_center_supports_create_list_and_retry(
    auth_headers,
) -> None:
    dashboard_snapshot_count_before = _count_report_snapshots("dashboard_summary", "v1")
    board_snapshot_count_before = _count_report_snapshots("board_tasks", "v1")

    create_response = client.post(
        "/api/v1/reports/recompute-tasks",
        json={
            "report_codes": ["dashboard_summary", "board_tasks"],
            "reason": "CODEX-TEST-M8-27-汇总快照重算",
        },
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-27-RECOMPUTE-CREATE"),
    )
    assert create_response.status_code == 202
    create_body = create_response.json()
    task_id = create_body["task"]["id"]
    assert create_body["message"] == "重算任务已创建，正在后台执行"

    list_response = client.get(
        "/api/v1/reports/recompute-tasks",
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-27-RECOMPUTE-LIST"),
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    task_row = next(item for item in list_body["items"] if item["id"] == task_id)
    assert task_row["status"] == "已完成"
    assert task_row["metric_version"] == "v1"
    assert task_row["reason"] == "CODEX-TEST-M8-27-汇总快照重算"
    assert set(task_row["report_codes"]) == {"dashboard_summary", "board_tasks"}
    assert "dashboard_summary" in task_row["result_payload"]
    assert "board_tasks" in task_row["result_payload"]

    ops_list_response = client.get(
        "/api/v1/reports/recompute-tasks",
        headers=_ops_admin_web_headers(
            auth_headers, "CODEX-TEST-M8-27-RECOMPUTE-OPS-LIST"
        ),
    )
    assert ops_list_response.status_code == 200
    assert any(item["id"] == task_id for item in ops_list_response.json()["items"])

    assert (
        _count_report_snapshots("dashboard_summary", "v1")
        > dashboard_snapshot_count_before
    )
    assert _count_report_snapshots("board_tasks", "v1") > board_snapshot_count_before

    blocked_create_response = client.post(
        "/api/v1/reports/recompute-tasks",
        json={
            "report_codes": ["dashboard_summary"],
            "reason": "CODEX-TEST-M8-27-RECOMPUTE-BLOCKED",
        },
        headers=_ops_admin_web_headers(
            auth_headers, "CODEX-TEST-M8-27-RECOMPUTE-BLOCKED"
        ),
    )
    assert blocked_create_response.status_code == 403
    assert blocked_create_response.json()["detail"] == "当前角色无权访问该接口"

    blocked_retry_response = client.post(
        f"/api/v1/reports/recompute-tasks/{task_id}/retry",
        headers=_ops_admin_web_headers(
            auth_headers, "CODEX-TEST-M8-27-RECOMPUTE-RETRY-BLOCKED"
        ),
    )
    assert blocked_retry_response.status_code == 403
    assert blocked_retry_response.json()["detail"] == "当前角色无权访问该接口"

    _mark_report_recompute_task_failed_for_test(task_id)
    retry_response = client.post(
        f"/api/v1/reports/recompute-tasks/{task_id}/retry",
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-27-RECOMPUTE-RETRY"),
    )
    assert retry_response.status_code == 202
    assert retry_response.json()["message"] == "重算任务已重新发起，正在后台执行"

    retried_task = _get_report_recompute_task(task_id)
    assert retried_task is not None
    assert retried_task.status == "已完成"
    assert retried_task.retry_count == 1


def test_summary_report_recompute_task_create_reuses_same_in_progress_task() -> None:
    actor = AuthenticatedActor(
        user_id="CODEX-TEST-M8-27-RECOMPUTE-IDEMPOTENT",
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )
    db = SessionLocal()
    try:
        first_dispatch = create_summary_report_recompute_task(
            db,
            actor=actor,
            metric_version="v1",
            report_codes=["dashboard_summary", "board_tasks"],
            reason="CODEX-TEST-M8-27-RECOMPUTE-IDEMPOTENT",
        )
        second_dispatch = create_summary_report_recompute_task(
            db,
            actor=actor,
            metric_version="v1",
            report_codes=["board_tasks", "dashboard_summary"],
            reason="CODEX-TEST-M8-27-RECOMPUTE-IDEMPOTENT",
        )
        assert first_dispatch.should_enqueue is True
        assert second_dispatch.should_enqueue is False
        assert first_dispatch.task.id == second_dispatch.task.id
    finally:
        db.close()


def test_summary_report_recompute_task_retry_blocks_pending_task(auth_headers) -> None:
    actor = AuthenticatedActor(
        user_id="CODEX-TEST-M8-27-RECOMPUTE-PENDING-RETRY",
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )
    db = SessionLocal()
    try:
        pending_dispatch = create_summary_report_recompute_task(
            db,
            actor=actor,
            metric_version="v1",
            report_codes=["light_overview"],
            reason="CODEX-TEST-M8-27-RECOMPUTE-PENDING-RETRY",
        )
    finally:
        db.close()

    retry_response = client.post(
        f"/api/v1/reports/recompute-tasks/{pending_dispatch.task.id}/retry",
        headers=_finance_headers(auth_headers, "CODEX-TEST-M8-27-PENDING-RETRY-API"),
    )
    assert retry_response.status_code == 409
    assert retry_response.json()["detail"] == "当前重算任务不支持重试"


def test_summary_report_recompute_task_retry_blocks_when_duplicate_pending_task_exists(
    auth_headers,
) -> None:
    actor = AuthenticatedActor(
        user_id="CODEX-TEST-M8-27-RECOMPUTE-DUPLICATE-RETRY",
        role_code="finance",
        company_id="CODEX-TEST-OPERATOR-COMPANY",
        company_type="operator_company",
        client_type="admin_web",
    )
    db = SessionLocal()
    try:
        failed_dispatch = create_summary_report_recompute_task(
            db,
            actor=actor,
            metric_version="v1",
            report_codes=["dashboard_summary"],
            reason="CODEX-TEST-M8-27-RECOMPUTE-DUPLICATE-RETRY",
        )
    finally:
        db.close()

    _mark_report_recompute_task_failed_for_test(failed_dispatch.task.id)

    db = SessionLocal()
    try:
        duplicate_dispatch = create_summary_report_recompute_task(
            db,
            actor=actor,
            metric_version="v1",
            report_codes=["dashboard_summary"],
            reason="CODEX-TEST-M8-27-RECOMPUTE-DUPLICATE-RETRY",
        )
        assert duplicate_dispatch.should_enqueue is True
    finally:
        db.close()

    retry_response = client.post(
        f"/api/v1/reports/recompute-tasks/{failed_dispatch.task.id}/retry",
        headers=_finance_headers(
            auth_headers, "CODEX-TEST-M8-27-RECOMPUTE-DUPLICATE-RETRY-API"
        ),
    )
    assert retry_response.status_code == 409
    assert (
        retry_response.json()["detail"]
        == "已存在相同范围的未完成重算任务，请直接查看当前任务结果"
    )


def test_report_metric_version_must_exist(auth_headers) -> None:
    response = client.get(
        "/api/v1/dashboard/summary",
        params={"metric_version": "v999"},
        headers=_ops_admin_web_headers(auth_headers, "CODEX-TEST-M7-VERSION-BLOCK"),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "当前报表口径版本不存在"


def test_daily_scan_merges_trigger_sources_without_duplicate_audit_logs(
    auth_headers,
) -> None:
    stagnant_sales_contract_id = _create_effective_sales_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    stagnant_purchase_contract_id = _create_effective_purchase_contract(
        auth_headers, qty_signed=Decimal("100.000")
    )
    stagnant_sales_order_id, _ = _create_sales_order_derived(
        auth_headers,
        sales_contract_id=stagnant_sales_contract_id,
        purchase_contract_id=stagnant_purchase_contract_id,
        qty=Decimal("40.000"),
        actual_receipt_amount=Decimal("0.00"),
        actual_pay_amount=Decimal("0.00"),
    )
    stagnant_outbound_doc_id = _create_system_outbound_doc(
        auth_headers,
        contract_id=stagnant_sales_contract_id,
        sales_order_id=stagnant_sales_order_id,
        source_ticket_no=f"CODEX-TEST-M8-26-MERGE-{uuid4().hex[:8]}",
        actual_qty=Decimal("40.000"),
    )
    _submit_outbound_doc(auth_headers, stagnant_outbound_doc_id, Decimal("40.000"))
    _backdate_contract_qty_effect(contract_id=stagnant_sales_contract_id, days_ago=5)
    _clear_daily_scan_audit_logs()

    board_response = client.get(
        "/api/v1/boards/tasks",
        headers=_ops_admin_web_headers(auth_headers, "CODEX-TEST-M8-26-MERGE-BOARD"),
    )
    assert board_response.status_code == 200

    dashboard_response = client.get(
        "/api/v1/dashboard/summary",
        headers=_ops_admin_web_headers(auth_headers, "CODEX-TEST-M8-26-MERGE-DASH"),
    )
    assert dashboard_response.status_code == 200

    light_response = client.get(
        "/api/v1/reports/light/overview",
        headers=auth_headers(
            user_id="CODEX-TEST-M8-26-MERGE-LIGHT",
            role_code="operations",
            company_id="CODEX-TEST-OPERATOR-COMPANY",
            company_type="operator_company",
            client_type="miniprogram",
        ),
    )
    assert light_response.status_code == 200

    scan_log = _get_daily_scan_audit_log(
        contract_id=stagnant_sales_contract_id,
        scan_type="fulfillment_stagnant",
    )
    assert scan_log is not None
    assert scan_log.extra_json["trigger_sources"] == [
        "board_tasks",
        "dashboard_summary",
        "light_overview",
    ]
    assert (
        _count_daily_scan_audit_logs(
            contract_id=stagnant_sales_contract_id,
            scan_type="fulfillment_stagnant",
        )
        == 1
    )


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
        fulfillment_stagnant_count = len(_list_fulfillment_stagnant_contract_ids(db))
        return {
            "pending_supplement_count": pending_supplement_count,
            "validation_failed_count": validation_failed_count,
            "qty_done_not_closed_count": qty_done_not_closed_count,
            "fulfillment_stagnant_count": fulfillment_stagnant_count,
            "total_alert_count": pending_supplement_count
            + validation_failed_count
            + qty_done_not_closed_count
            + fulfillment_stagnant_count,
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
            "fulfillment_stagnant_count": board_metrics["fulfillment_stagnant_count"],
        }
    finally:
        db.close()


def _list_fulfillment_stagnant_contract_ids(db) -> list[int]:
    contracts = db.scalars(
        select(Contract).where(Contract.status == "生效中").order_by(Contract.id.asc())
    ).all()
    if not contracts:
        return []
    contract_ids = {contract.id for contract in contracts}
    effect_rows = db.execute(
        select(ContractItem.contract_id, ContractQtyEffect.created_at)
        .join(ContractQtyEffect, ContractQtyEffect.contract_item_id == ContractItem.id)
        .where(ContractItem.contract_id.in_(contract_ids))
        .order_by(ContractItem.contract_id.asc(), ContractQtyEffect.created_at.desc())
    ).all()
    latest_effect_map: dict[int, datetime] = {}
    for contract_id, created_at in effect_rows:
        if int(contract_id) not in latest_effect_map:
            latest_effect_map[int(contract_id)] = created_at

    today_cn = datetime.now(SHANGHAI_TZ).date()
    stagnant_ids: list[int] = []
    for contract in contracts:
        reference_time = (
            latest_effect_map.get(contract.id)
            or contract.approved_at
            or contract.submitted_at
            or contract.created_at
        )
        assert reference_time is not None
        if (today_cn - reference_time.astimezone(SHANGHAI_TZ).date()).days >= 3:
            stagnant_ids.append(contract.id)
    return stagnant_ids


def _backdate_contract_qty_effect(*, contract_id: int, days_ago: int) -> None:
    db = SessionLocal()
    try:
        effect = db.scalar(
            select(ContractQtyEffect)
            .join(ContractItem, ContractItem.id == ContractQtyEffect.contract_item_id)
            .where(ContractItem.contract_id == contract_id)
            .order_by(ContractQtyEffect.created_at.desc(), ContractQtyEffect.id.desc())
            .limit(1)
        )
        contract = db.get(Contract, contract_id)
        assert effect is not None
        assert contract is not None
        target_time = datetime.now(UTC) - timedelta(days=days_ago)
        effect.created_at = target_time
        contract.updated_at = target_time
        db.commit()
    finally:
        db.close()


def _count_daily_scan_audit_logs(*, contract_id: int, scan_type: str) -> int:
    db = SessionLocal()
    try:
        return len(
            db.scalars(
                select(BusinessAuditLog).where(
                    BusinessAuditLog.biz_type == "report_daily_contract_scan",
                    BusinessAuditLog.biz_id
                    == _scan_audit_biz_id(
                        contract_id=contract_id,
                        scan_type=scan_type,
                    ),
                )
            ).all()
        )
    finally:
        db.close()


def _get_daily_scan_audit_log(
    *, contract_id: int, scan_type: str
) -> BusinessAuditLog | None:
    db = SessionLocal()
    try:
        return db.scalar(
            select(BusinessAuditLog).where(
                BusinessAuditLog.biz_type == "report_daily_contract_scan",
                BusinessAuditLog.biz_id
                == _scan_audit_biz_id(
                    contract_id=contract_id,
                    scan_type=scan_type,
                ),
            )
        )
    finally:
        db.close()


def _scan_audit_biz_id(*, contract_id: int, scan_type: str) -> str:
    return f"{scan_type}:{contract_id}:{datetime.now(SHANGHAI_TZ).date().isoformat()}"


def _clear_daily_scan_audit_logs() -> None:
    db = SessionLocal()
    try:
        scan_day = datetime.now(SHANGHAI_TZ).date().isoformat()
        logs = db.scalars(
            select(BusinessAuditLog).where(
                BusinessAuditLog.biz_type.in_(
                    [
                        "report_daily_contract_scan",
                        "report_daily_contract_scan_state",
                    ]
                ),
                BusinessAuditLog.biz_id.like(f"%:{scan_day}"),
            )
        ).all()
        for log in logs:
            db.delete(log)
        db.commit()
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


def _count_report_snapshots(report_code: str, version: str) -> int:
    db = SessionLocal()
    try:
        return len(
            db.scalars(
                select(ReportSnapshot).where(
                    ReportSnapshot.report_code == report_code,
                    ReportSnapshot.version == version,
                )
            ).all()
        )
    finally:
        db.close()


def _get_report_export_task(task_id: int) -> ReportExportTask | None:
    db = SessionLocal()
    try:
        return db.get(ReportExportTask, task_id)
    finally:
        db.close()


def _get_report_recompute_task(task_id: int) -> ReportRecomputeTask | None:
    db = SessionLocal()
    try:
        return db.get(ReportRecomputeTask, task_id)
    finally:
        db.close()


def _mark_report_recompute_task_failed_for_test(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(ReportRecomputeTask, task_id)
        assert task is not None
        task.status = "已失败"
        task.idempotency_key = f"{task.idempotency_key}:failed:{task.id}"
        task.error_message = "CODEX-TEST-M8-27-重算失败"
        task.result_payload = {}
        task.finished_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()


def _resolve_report_export_task_file_path(relative_path: str) -> Path:
    export_root = Path(os.environ["REPORT_EXPORT_DIR"])
    return (export_root / relative_path).resolve()


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
