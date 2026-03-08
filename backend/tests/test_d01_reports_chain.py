from __future__ import annotations

from datetime import date
from decimal import Decimal

from tests import test_m7_reports as reports_helpers


def test_d01_reports_chain_summary_board_light_and_scan_audit(auth_headers) -> None:
    artifact_baseline = _capture_report_artifact_baseline()
    sales_contract_id: int | None = None
    purchase_contract_id: int | None = None
    stagnant_sales_contract_id: int | None = None
    stagnant_purchase_contract_id: int | None = None
    try:
        sales_contract_id = reports_helpers._create_effective_sales_contract(
            auth_headers,
            qty_signed=Decimal("100.000"),
        )
        purchase_contract_id = reports_helpers._create_effective_purchase_contract(
            auth_headers,
            qty_signed=Decimal("100.000"),
        )
        sales_order_id, _ = reports_helpers._create_sales_order_derived(
            auth_headers,
            sales_contract_id=sales_contract_id,
            purchase_contract_id=purchase_contract_id,
            qty=Decimal("100.000"),
            actual_receipt_amount=Decimal("600025.00"),
            actual_pay_amount=Decimal("580080.00"),
        )

        reports_helpers._confirm_receipt_doc(
            auth_headers,
            reports_helpers._query_receipt_doc(
                contract_id=sales_contract_id, doc_type="DEPOSIT"
            ).id,
            Decimal("50000.00"),
        )
        reports_helpers._confirm_receipt_doc(
            auth_headers,
            reports_helpers._query_receipt_doc(
                contract_id=sales_contract_id,
                sales_order_id=sales_order_id,
                doc_type="NORMAL",
            ).id,
            Decimal("600025.00"),
        )
        reports_helpers._confirm_payment_doc(
            auth_headers,
            reports_helpers._query_payment_doc(
                contract_id=purchase_contract_id, doc_type="DEPOSIT"
            ).id,
            Decimal("50000.00"),
        )
        reports_helpers._confirm_payment_doc(
            auth_headers,
            reports_helpers._query_payment_doc(
                contract_id=purchase_contract_id,
                purchase_order_sales_order_id=sales_order_id,
                doc_type="NORMAL",
            ).id,
            Decimal("580080.00"),
        )
        reports_helpers._submit_inbound_doc(
            auth_headers,
            reports_helpers._query_inbound_doc(contract_id=purchase_contract_id).id,
            Decimal("100.000"),
        )
        outbound_doc_id = reports_helpers._create_system_outbound_doc(
            auth_headers,
            contract_id=sales_contract_id,
            sales_order_id=sales_order_id,
            source_ticket_no="CODEX-TEST-D01-REPORTS-OUT-001",
            actual_qty=Decimal("100.000"),
        )
        reports_helpers._submit_outbound_doc(
            auth_headers,
            outbound_doc_id,
            Decimal("100.000"),
        )

        stagnant_sales_contract_id = reports_helpers._create_effective_sales_contract(
            auth_headers,
            qty_signed=Decimal("40.000"),
        )
        stagnant_purchase_contract_id = (
            reports_helpers._create_effective_purchase_contract(
                auth_headers,
                qty_signed=Decimal("40.000"),
            )
        )
        stagnant_sales_order_id, _ = reports_helpers._create_sales_order_derived(
            auth_headers,
            sales_contract_id=stagnant_sales_contract_id,
            purchase_contract_id=stagnant_purchase_contract_id,
            qty=Decimal("40.000"),
            actual_receipt_amount=Decimal("0.00"),
            actual_pay_amount=Decimal("0.00"),
        )
        stagnant_outbound_doc_id = reports_helpers._create_system_outbound_doc(
            auth_headers,
            contract_id=stagnant_sales_contract_id,
            sales_order_id=stagnant_sales_order_id,
            source_ticket_no="CODEX-TEST-D01-REPORTS-STAGNANT-001",
            actual_qty=Decimal("20.000"),
        )
        reports_helpers._submit_outbound_doc(
            auth_headers,
            stagnant_outbound_doc_id,
            Decimal("20.000"),
        )
        reports_helpers._backdate_contract_qty_effect(
            contract_id=stagnant_sales_contract_id,
            days_ago=5,
        )

        dashboard_response = reports_helpers.client.get(
            "/api/v1/dashboard/summary",
            headers=reports_helpers._ops_admin_web_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-DASH",
            ),
        )
        assert dashboard_response.status_code == 200
        dashboard_body = dashboard_response.json()
        dashboard_expected = reports_helpers._compute_expected_dashboard_metrics()
        assert (
            Decimal(str(dashboard_body["contract_execution_rate"]))
            == dashboard_expected["contract_execution_rate"]
        )
        assert (
            dashboard_body["threshold_alert_count"]
            == dashboard_expected["threshold_alert_count"]
        )

        board_response = reports_helpers.client.get(
            "/api/v1/boards/tasks",
            headers=reports_helpers._ops_admin_web_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-BOARD",
            ),
        )
        assert board_response.status_code == 200
        board_body = board_response.json()
        board_expected = reports_helpers._compute_expected_board_metrics()
        assert (
            board_body["qty_done_not_closed_count"]
            == board_expected["qty_done_not_closed_count"]
        )
        assert (
            board_body["fulfillment_stagnant_count"]
            == board_expected["fulfillment_stagnant_count"]
        )

        light_response = reports_helpers.client.get(
            "/api/v1/reports/light/overview",
            headers=auth_headers(
                user_id="CODEX-TEST-D01-REPORTS-LIGHT",
                role_code="operations",
                company_id="CODEX-TEST-OPERATOR-COMPANY",
                company_type="operator_company",
                client_type="miniprogram",
            ),
        )
        assert light_response.status_code == 200
        light_body = light_response.json()
        light_expected = reports_helpers._compute_expected_light_metrics()
        assert (
            Decimal(str(light_body["actual_receipt_today"]))
            == light_expected["actual_receipt_today"]
        )
        assert light_body["abnormal_count"] == light_expected["abnormal_count"]

        assert board_body["fulfillment_stagnant_count"] >= 1
        assert light_body["fulfillment_stagnant_count"] >= 1
    finally:
        if sales_contract_id is not None:
            _set_contract_status(sales_contract_id, "已关闭")
        if purchase_contract_id is not None:
            _set_contract_status(purchase_contract_id, "已归档")
        if stagnant_sales_contract_id is not None:
            _set_contract_status(stagnant_sales_contract_id, "已归档")
        if stagnant_purchase_contract_id is not None:
            _set_contract_status(stagnant_purchase_contract_id, "已归档")
        _cleanup_report_artifacts(artifact_baseline)


def test_d01_reports_chain_multi_dim_export_and_recompute(auth_headers) -> None:
    artifact_baseline = _capture_report_artifact_baseline()
    try:
        sales_contract_id = reports_helpers._create_effective_sales_contract(
            auth_headers,
            qty_signed=Decimal("50.000"),
        )
        purchase_contract_id = reports_helpers._create_effective_purchase_contract(
            auth_headers,
            qty_signed=Decimal("50.000"),
        )
        receipt_doc = reports_helpers._query_receipt_doc(
            contract_id=sales_contract_id,
            doc_type="DEPOSIT",
        )
        payment_doc = reports_helpers._query_payment_doc(
            contract_id=purchase_contract_id,
            doc_type="DEPOSIT",
        )
        reports_helpers._confirm_receipt_doc(
            auth_headers,
            receipt_doc.id,
            Decimal("15000.00"),
        )
        reports_helpers._confirm_payment_doc(
            auth_headers,
            payment_doc.id,
            Decimal("12000.00"),
        )

        refund_request_response = reports_helpers.client.post(
            f"/api/v1/payment-docs/{payment_doc.id}/refund-request",
            json={
                "refund_amount": 1000.00,
                "reason": "CODEX-TEST-D01-REPORTS-REFUND-REQUEST",
            },
            headers=reports_helpers._finance_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-REFUND-REQUEST",
            ),
        )
        assert refund_request_response.status_code == 200

        multi_dim_response = reports_helpers.client.get(
            "/api/v1/reports/admin/multi-dim",
            params={
                "group_by": "refund_status",
                "contract_direction": "purchase",
                "date_from": date.today().isoformat(),
                "date_to": date.today().isoformat(),
            },
            headers=reports_helpers._ops_admin_web_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-MULTI-DIM",
            ),
        )
        assert multi_dim_response.status_code == 200
        assert any(
            row["dimension_value"] == "待审核"
            for row in multi_dim_response.json()["rows"]
        )

        export_create_response = reports_helpers.client.post(
            "/api/v1/reports/admin/multi-dim/export-tasks",
            json={
                "group_by": "refund_status",
                "contract_direction": "purchase",
                "date_from": date.today().isoformat(),
                "date_to": date.today().isoformat(),
            },
            headers=reports_helpers._finance_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-EXPORT-CREATE",
            ),
        )
        assert export_create_response.status_code == 202
        export_task_id = export_create_response.json()["task"]["id"]

        export_list_response = reports_helpers.client.get(
            "/api/v1/reports/admin/multi-dim/export-tasks",
            headers=reports_helpers._finance_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-EXPORT-LIST",
            ),
        )
        assert export_list_response.status_code == 200
        export_task_row = next(
            item
            for item in export_list_response.json()["items"]
            if item["id"] == export_task_id
        )
        assert export_task_row["status"] == "已完成"

        export_download_response = reports_helpers.client.get(
            f"/api/v1/reports/admin/multi-dim/export-tasks/{export_task_id}/download",
            headers=reports_helpers._finance_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-EXPORT-DOWNLOAD",
            ),
        )
        assert export_download_response.status_code == 200
        assert "待审核" in export_download_response.text

        recompute_before = reports_helpers._count_report_snapshots(
            "dashboard_summary", "v1"
        )
        recompute_response = reports_helpers.client.post(
            "/api/v1/reports/recompute-tasks",
            json={
                "report_codes": ["dashboard_summary", "board_tasks", "light_overview"],
                "reason": "CODEX-TEST-D01-REPORTS-RECOMPUTE",
            },
            headers=reports_helpers._finance_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-RECOMPUTE",
            ),
        )
        assert recompute_response.status_code == 202
        recompute_task_id = recompute_response.json()["task"]["id"]

        recompute_list_response = reports_helpers.client.get(
            "/api/v1/reports/recompute-tasks",
            headers=reports_helpers._finance_headers(
                auth_headers,
                "CODEX-TEST-D01-REPORTS-RECOMPUTE-LIST",
            ),
        )
        assert recompute_list_response.status_code == 200
        recompute_task_row = next(
            item
            for item in recompute_list_response.json()["items"]
            if item["id"] == recompute_task_id
        )
        assert recompute_task_row["status"] == "已完成"
        assert set(recompute_task_row["report_codes"]) == {
            "dashboard_summary",
            "board_tasks",
            "light_overview",
        }
        assert (
            reports_helpers._count_report_snapshots("dashboard_summary", "v1")
            > recompute_before
        )
    finally:
        _cleanup_report_artifacts(artifact_baseline)


def _set_contract_status(contract_id: int, status: str) -> None:
    db = reports_helpers.SessionLocal()
    try:
        contract = db.get(reports_helpers.Contract, contract_id)
        assert contract is not None
        contract.status = status
        db.commit()
    finally:
        db.close()


def _capture_report_artifact_baseline() -> dict[str, set[int]]:
    db = reports_helpers.SessionLocal()
    try:
        return {
            "snapshot_ids": {
                int(row.id)
                for row in db.scalars(
                    reports_helpers.select(reports_helpers.ReportSnapshot)
                ).all()
            },
            "export_task_ids": {
                int(row.id)
                for row in db.scalars(
                    reports_helpers.select(reports_helpers.ReportExportTask)
                ).all()
            },
            "recompute_task_ids": {
                int(row.id)
                for row in db.scalars(
                    reports_helpers.select(reports_helpers.ReportRecomputeTask)
                ).all()
            },
            "audit_log_ids": {
                int(row.id)
                for row in db.scalars(
                    reports_helpers.select(reports_helpers.BusinessAuditLog).where(
                        reports_helpers.BusinessAuditLog.biz_type.in_(
                            [
                                "report_daily_contract_scan",
                                "report_daily_contract_scan_state",
                            ]
                        )
                    )
                ).all()
            },
        }
    finally:
        db.close()


def _cleanup_report_artifacts(artifact_baseline: dict[str, set[int]]) -> None:
    db = reports_helpers.SessionLocal()
    try:
        for row in db.scalars(
            reports_helpers.select(reports_helpers.ReportSnapshot)
        ).all():
            if int(row.id) not in artifact_baseline["snapshot_ids"]:
                db.delete(row)
        export_tasks = db.scalars(
            reports_helpers.select(reports_helpers.ReportExportTask)
        ).all()
        for row in export_tasks:
            if int(row.id) in artifact_baseline["export_task_ids"]:
                continue
            if row.file_path:
                export_file_path = (
                    reports_helpers._resolve_report_export_task_file_path(row.file_path)
                )
                if export_file_path.exists():
                    export_file_path.unlink()
            db.delete(row)
        for row in db.scalars(
            reports_helpers.select(reports_helpers.ReportRecomputeTask)
        ).all():
            if int(row.id) not in artifact_baseline["recompute_task_ids"]:
                db.delete(row)
        for row in db.scalars(
            reports_helpers.select(reports_helpers.BusinessAuditLog).where(
                reports_helpers.BusinessAuditLog.biz_type.in_(
                    [
                        "report_daily_contract_scan",
                        "report_daily_contract_scan_state",
                    ]
                )
            )
        ).all():
            if int(row.id) not in artifact_baseline["audit_log_ids"]:
                db.delete(row)
        db.commit()
    finally:
        db.close()
