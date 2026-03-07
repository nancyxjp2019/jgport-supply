from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.contract import Contract
from app.models.inbound_doc import InboundDoc
from app.models.outbound_doc import OutboundDoc
from app.models.payment_doc import PaymentDoc
from app.models.receipt_doc import ReceiptDoc
from app.models.report_snapshot import ReportSnapshot

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

METRIC_VERSION_V1 = "v1"
REPORT_CODE_DASHBOARD = "dashboard_summary"
REPORT_CODE_BOARD = "board_tasks"
REPORT_CODE_LIGHT = "light_overview"
GROUP_BY_CONTRACT_DIRECTION = "contract_direction"
GROUP_BY_DOC_STATUS = "doc_status"
GROUP_BY_REFUND_STATUS = "refund_status"
ALLOWED_MULTI_DIM_GROUPS = {
    GROUP_BY_CONTRACT_DIRECTION,
    GROUP_BY_DOC_STATUS,
    GROUP_BY_REFUND_STATUS,
}
SLA_MINUTES_T0 = 5

MONEY_PRECISION = Decimal("0.01")
QTY_PRECISION = Decimal("0.001")
RATE_PRECISION = Decimal("0.000001")

CONTRACT_DIRECTION_PURCHASE = "purchase"
CONTRACT_DIRECTION_SALES = "sales"
CONTRACT_STATUS_EFFECTIVE_SCOPE = {
    "生效中",
    "数量履约完成",
    "已关闭",
    "手工关闭",
    "已归档",
}
CONTRACT_STATUS_QTY_DONE = "数量履约完成"
DOC_STATUS_CONFIRMED_SCOPE = {"已确认", "已核销"}
DOC_STATUS_PENDING_SUPPLEMENT = "待补录金额"
DOC_STATUS_VALIDATION_FAILED = "校验失败"
DOC_STATUS_POSTED = "已过账"
REFUND_STATUS_PENDING_REVIEW = "待审核"
SLA_STATUS_NORMAL = "正常"
SLA_STATUS_DELAYED = "延迟"


@dataclass(frozen=True)
class ReportSnapshotResult:
    metric_version: str
    snapshot_time: datetime
    sla_status: str
    payload: dict


@dataclass(frozen=True)
class AdminMultiDimRowResult:
    dimension: str
    dimension_value: str
    receipt_net_amount: Decimal
    payment_net_amount: Decimal
    net_cashflow: Decimal
    receipt_doc_count: int
    payment_doc_count: int
    pending_supplement_count: int
    refund_pending_review_count: int


@dataclass(frozen=True)
class AdminMultiDimReportResult:
    metric_version: str
    snapshot_time: datetime
    sla_status: str
    group_by: str
    filters: dict[str, str | None]
    total_receipt_net_amount: Decimal
    total_payment_net_amount: Decimal
    total_net_cashflow: Decimal
    rows: list[AdminMultiDimRowResult]


class ReportServiceError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def get_dashboard_summary(
    db: Session, *, metric_version: str | None
) -> ReportSnapshotResult:
    version = _resolve_metric_version(metric_version)
    snapshot = _get_or_create_snapshot(
        db,
        report_code=REPORT_CODE_DASHBOARD,
        version=version,
        builder=_build_dashboard_payload,
    )
    return ReportSnapshotResult(
        metric_version=snapshot.version,
        snapshot_time=snapshot.snapshot_time,
        sla_status=_resolve_sla_status(snapshot.snapshot_time),
        payload=snapshot.metric_payload,
    )


def get_board_tasks(db: Session, *, metric_version: str | None) -> ReportSnapshotResult:
    version = _resolve_metric_version(metric_version)
    snapshot = _get_or_create_snapshot(
        db,
        report_code=REPORT_CODE_BOARD,
        version=version,
        builder=_build_board_payload,
    )
    return ReportSnapshotResult(
        metric_version=snapshot.version,
        snapshot_time=snapshot.snapshot_time,
        sla_status=_resolve_sla_status(snapshot.snapshot_time),
        payload=snapshot.metric_payload,
    )


def get_light_overview(
    db: Session, *, metric_version: str | None
) -> ReportSnapshotResult:
    version = _resolve_metric_version(metric_version)
    snapshot = _get_or_create_snapshot(
        db,
        report_code=REPORT_CODE_LIGHT,
        version=version,
        builder=_build_light_payload,
    )
    return ReportSnapshotResult(
        metric_version=snapshot.version,
        snapshot_time=snapshot.snapshot_time,
        sla_status=_resolve_sla_status(snapshot.snapshot_time),
        payload=snapshot.metric_payload,
    )


def get_admin_multi_dim_report(
    db: Session,
    *,
    metric_version: str | None,
    group_by: str,
    contract_direction: str | None,
    doc_status: str | None,
    refund_status: str | None,
    date_from: date | None,
    date_to: date | None,
) -> AdminMultiDimReportResult:
    version = _resolve_metric_version(metric_version)
    _ensure_multi_dim_group_by(group_by)
    start_utc, end_utc = _resolve_optional_date_window_utc(
        date_from=date_from,
        date_to=date_to,
    )

    receipt_docs = db.scalars(select(ReceiptDoc)).all()
    payment_docs = db.scalars(select(PaymentDoc)).all()
    contract_directions = _load_contract_direction_map(
        db,
        contract_ids={
            *(doc.contract_id for doc in receipt_docs),
            *(doc.contract_id for doc in payment_docs),
        },
    )

    buckets: dict[str, dict[str, Decimal | int | str]] = {}
    for receipt_doc in receipt_docs:
        resolved_direction = contract_directions.get(receipt_doc.contract_id)
        if not _passes_multi_dim_filters(
            contract_direction=resolved_direction,
            doc_status=receipt_doc.status,
            refund_status=receipt_doc.refund_status,
            created_at=receipt_doc.created_at,
            expected_contract_direction=contract_direction,
            expected_doc_status=doc_status,
            expected_refund_status=refund_status,
            start_utc=start_utc,
            end_utc=end_utc,
        ):
            continue
        group_value = _resolve_group_value(
            group_by,
            contract_direction=resolved_direction,
            doc_status=receipt_doc.status,
            refund_status=receipt_doc.refund_status,
        )
        bucket = _get_or_init_multi_dim_bucket(
            buckets,
            group_by=group_by,
            group_value=group_value,
        )
        bucket["receipt_net_amount"] = Decimal(
            str(bucket["receipt_net_amount"])
        ) + _calculate_fund_net_amount(
            receipt_doc.amount_actual,
            receipt_doc.refund_amount,
        )
        bucket["receipt_doc_count"] = int(bucket["receipt_doc_count"]) + 1
        if receipt_doc.status == DOC_STATUS_PENDING_SUPPLEMENT:
            bucket["pending_supplement_count"] = (
                int(bucket["pending_supplement_count"]) + 1
            )
        if receipt_doc.refund_status == REFUND_STATUS_PENDING_REVIEW:
            bucket["refund_pending_review_count"] = (
                int(bucket["refund_pending_review_count"]) + 1
            )

    for payment_doc in payment_docs:
        resolved_direction = contract_directions.get(payment_doc.contract_id)
        if not _passes_multi_dim_filters(
            contract_direction=resolved_direction,
            doc_status=payment_doc.status,
            refund_status=payment_doc.refund_status,
            created_at=payment_doc.created_at,
            expected_contract_direction=contract_direction,
            expected_doc_status=doc_status,
            expected_refund_status=refund_status,
            start_utc=start_utc,
            end_utc=end_utc,
        ):
            continue
        group_value = _resolve_group_value(
            group_by,
            contract_direction=resolved_direction,
            doc_status=payment_doc.status,
            refund_status=payment_doc.refund_status,
        )
        bucket = _get_or_init_multi_dim_bucket(
            buckets,
            group_by=group_by,
            group_value=group_value,
        )
        bucket["payment_net_amount"] = Decimal(
            str(bucket["payment_net_amount"])
        ) + _calculate_fund_net_amount(
            payment_doc.amount_actual,
            payment_doc.refund_amount,
        )
        bucket["payment_doc_count"] = int(bucket["payment_doc_count"]) + 1
        if payment_doc.status == DOC_STATUS_PENDING_SUPPLEMENT:
            bucket["pending_supplement_count"] = (
                int(bucket["pending_supplement_count"]) + 1
            )
        if payment_doc.refund_status == REFUND_STATUS_PENDING_REVIEW:
            bucket["refund_pending_review_count"] = (
                int(bucket["refund_pending_review_count"]) + 1
            )

    rows: list[AdminMultiDimRowResult] = []
    for group_value, payload in sorted(buckets.items(), key=lambda item: item[0]):
        receipt_net_amount = Decimal(str(payload["receipt_net_amount"])).quantize(
            MONEY_PRECISION
        )
        payment_net_amount = Decimal(str(payload["payment_net_amount"])).quantize(
            MONEY_PRECISION
        )
        rows.append(
            AdminMultiDimRowResult(
                dimension=str(payload["dimension"]),
                dimension_value=group_value,
                receipt_net_amount=receipt_net_amount,
                payment_net_amount=payment_net_amount,
                net_cashflow=(receipt_net_amount - payment_net_amount).quantize(
                    MONEY_PRECISION
                ),
                receipt_doc_count=int(payload["receipt_doc_count"]),
                payment_doc_count=int(payload["payment_doc_count"]),
                pending_supplement_count=int(payload["pending_supplement_count"]),
                refund_pending_review_count=int(payload["refund_pending_review_count"]),
            )
        )

    total_receipt = sum(
        (row.receipt_net_amount for row in rows),
        Decimal("0.00"),
    ).quantize(MONEY_PRECISION)
    total_payment = sum(
        (row.payment_net_amount for row in rows),
        Decimal("0.00"),
    ).quantize(MONEY_PRECISION)
    now = datetime.now(UTC)
    return AdminMultiDimReportResult(
        metric_version=version,
        snapshot_time=now,
        sla_status=_resolve_sla_status(now),
        group_by=group_by,
        filters={
            "contract_direction": contract_direction,
            "doc_status": doc_status,
            "refund_status": refund_status,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
        total_receipt_net_amount=total_receipt,
        total_payment_net_amount=total_payment,
        total_net_cashflow=(total_receipt - total_payment).quantize(MONEY_PRECISION),
        rows=rows,
    )


def build_admin_multi_dim_report_csv(report: AdminMultiDimReportResult) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "维度",
            "维度值",
            "收款净额",
            "付款净额",
            "资金净流入",
            "收款单数",
            "付款单数",
            "待补录数量",
            "待审核退款数量",
        ]
    )
    for row in report.rows:
        writer.writerow(
            [
                row.dimension,
                row.dimension_value,
                str(row.receipt_net_amount),
                str(row.payment_net_amount),
                str(row.net_cashflow),
                row.receipt_doc_count,
                row.payment_doc_count,
                row.pending_supplement_count,
                row.refund_pending_review_count,
            ]
        )
    return "\ufeff" + output.getvalue()


def _resolve_metric_version(metric_version: str | None) -> str:
    if metric_version in {None, "", METRIC_VERSION_V1}:
        return METRIC_VERSION_V1
    raise ReportServiceError(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="当前报表口径版本不存在",
    )


def _get_or_create_snapshot(
    db: Session,
    *,
    report_code: str,
    version: str,
    builder,
) -> ReportSnapshot:
    latest = db.scalar(
        select(ReportSnapshot)
        .where(
            ReportSnapshot.report_code == report_code, ReportSnapshot.version == version
        )
        .order_by(ReportSnapshot.snapshot_time.desc(), ReportSnapshot.id.desc())
        .limit(1)
    )
    payload = builder(db)
    now = datetime.now(UTC)
    should_insert = (
        latest is None
        or latest.metric_payload != payload
        or _is_snapshot_stale(latest.snapshot_time, now)
    )
    if not should_insert:
        return latest

    snapshot = ReportSnapshot(
        report_code=report_code,
        version=version,
        metric_payload=payload,
    )
    db.add(snapshot)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise ReportServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="报表快照写入失败，请稍后重试",
        ) from exc
    db.refresh(snapshot)
    return snapshot


def _is_snapshot_stale(snapshot_time: datetime, now: datetime) -> bool:
    return now - snapshot_time.astimezone(UTC) > timedelta(minutes=SLA_MINUTES_T0)


def _resolve_sla_status(snapshot_time: datetime) -> str:
    if _is_snapshot_stale(snapshot_time, datetime.now(UTC)):
        return SLA_STATUS_DELAYED
    return SLA_STATUS_NORMAL


def _build_dashboard_payload(db: Session) -> dict:
    receipt_today = _sum_receipt_today(db)
    payment_today = _sum_payment_today(db)
    inventory_turnover = _calculate_inventory_turnover(db)
    execution_rate = _calculate_contract_execution_rate(db)
    alert_count, _, _, _ = _collect_board_buckets(db)
    return {
        "contract_execution_rate": str(execution_rate),
        "actual_receipt_today": str(receipt_today),
        "actual_payment_today": str(payment_today),
        "inventory_turnover_30d": str(inventory_turnover),
        "threshold_alert_count": alert_count,
    }


def _build_board_payload(db: Session) -> dict:
    total_alert_count, pending_items, validation_items, qty_done_items = (
        _collect_board_buckets(db)
    )
    _ = total_alert_count
    return {
        "pending_supplement_count": len(pending_items),
        "validation_failed_count": len(validation_items),
        "qty_done_not_closed_count": len(qty_done_items),
        "pending_supplement_items": pending_items[:10],
        "validation_failed_items": validation_items[:10],
        "qty_done_not_closed_items": qty_done_items[:10],
    }


def _build_light_payload(db: Session) -> dict:
    receipt_today = _sum_receipt_today(db)
    payment_today = _sum_payment_today(db)
    inbound_today = _sum_inbound_today(db)
    outbound_today = _sum_outbound_today(db)
    alert_count, pending_items, validation_items, qty_done_items = (
        _collect_board_buckets(db)
    )
    return {
        "actual_receipt_today": str(receipt_today),
        "actual_payment_today": str(payment_today),
        "inbound_qty_today": str(inbound_today),
        "outbound_qty_today": str(outbound_today),
        "abnormal_count": alert_count,
        "pending_supplement_count": len(pending_items),
        "validation_failed_count": len(validation_items),
        "qty_done_not_closed_count": len(qty_done_items),
    }


def _calculate_contract_execution_rate(db: Session) -> Decimal:
    contracts = db.scalars(
        select(Contract)
        .options(selectinload(Contract.items))
        .where(Contract.status.in_(CONTRACT_STATUS_EFFECTIVE_SCOPE))
    ).all()
    total_signed = Decimal("0.000")
    total_done = Decimal("0.000")
    for contract in contracts:
        for item in contract.items:
            signed_qty = Decimal(str(item.qty_signed))
            done_qty = Decimal(
                str(
                    item.qty_in_acc
                    if contract.direction == CONTRACT_DIRECTION_PURCHASE
                    else item.qty_out_acc
                )
            )
            total_signed += signed_qty
            total_done += min(done_qty, signed_qty)
    if total_signed <= Decimal("0.000"):
        return Decimal("0.000000")
    return (total_done / total_signed).quantize(RATE_PRECISION)


def _calculate_inventory_turnover(db: Session) -> Decimal:
    recent_start, recent_end = _recent_30_day_window_utc()
    inbound_docs = db.scalars(
        select(InboundDoc).where(InboundDoc.status == DOC_STATUS_POSTED)
    ).all()
    outbound_docs = db.scalars(
        select(OutboundDoc).where(OutboundDoc.status == DOC_STATUS_POSTED)
    ).all()

    current_available_stock = Decimal("0.000")
    for inbound_doc in inbound_docs:
        current_available_stock += Decimal(str(inbound_doc.actual_qty))
    for outbound_doc in outbound_docs:
        current_available_stock -= Decimal(str(outbound_doc.actual_qty))

    if current_available_stock <= Decimal("0.000"):
        return Decimal("0.000000")

    recent_outbound_total = Decimal("0.000")
    for outbound_doc in outbound_docs:
        if outbound_doc.submitted_at is None:
            continue
        if recent_start <= outbound_doc.submitted_at.astimezone(UTC) < recent_end:
            recent_outbound_total += Decimal(str(outbound_doc.actual_qty))
    return (recent_outbound_total / current_available_stock).quantize(RATE_PRECISION)


def _sum_receipt_today(db: Session) -> Decimal:
    start_utc, end_utc = _today_window_utc()
    docs = db.scalars(
        select(ReceiptDoc).where(ReceiptDoc.status.in_(DOC_STATUS_CONFIRMED_SCOPE))
    ).all()
    total = Decimal("0.00")
    for doc in docs:
        if doc.confirmed_at is None:
            continue
        confirmed_at = doc.confirmed_at.astimezone(UTC)
        if start_utc <= confirmed_at < end_utc:
            total += _calculate_fund_net_amount(doc.amount_actual, doc.refund_amount)
    return total.quantize(MONEY_PRECISION)


def _sum_payment_today(db: Session) -> Decimal:
    start_utc, end_utc = _today_window_utc()
    docs = db.scalars(
        select(PaymentDoc).where(PaymentDoc.status.in_(DOC_STATUS_CONFIRMED_SCOPE))
    ).all()
    total = Decimal("0.00")
    for doc in docs:
        if doc.confirmed_at is None:
            continue
        confirmed_at = doc.confirmed_at.astimezone(UTC)
        if start_utc <= confirmed_at < end_utc:
            total += _calculate_fund_net_amount(doc.amount_actual, doc.refund_amount)
    return total.quantize(MONEY_PRECISION)


def _sum_inbound_today(db: Session) -> Decimal:
    start_utc, end_utc = _today_window_utc()
    docs = db.scalars(
        select(InboundDoc).where(InboundDoc.status == DOC_STATUS_POSTED)
    ).all()
    total = Decimal("0.000")
    for doc in docs:
        if doc.submitted_at is None:
            continue
        submitted_at = doc.submitted_at.astimezone(UTC)
        if start_utc <= submitted_at < end_utc:
            total += Decimal(str(doc.actual_qty))
    return total.quantize(QTY_PRECISION)


def _sum_outbound_today(db: Session) -> Decimal:
    start_utc, end_utc = _today_window_utc()
    docs = db.scalars(
        select(OutboundDoc).where(OutboundDoc.status == DOC_STATUS_POSTED)
    ).all()
    total = Decimal("0.000")
    for doc in docs:
        if doc.submitted_at is None:
            continue
        submitted_at = doc.submitted_at.astimezone(UTC)
        if start_utc <= submitted_at < end_utc:
            total += Decimal(str(doc.actual_qty))
    return total.quantize(QTY_PRECISION)


def _collect_board_buckets(
    db: Session,
) -> tuple[int, list[dict], list[dict], list[dict]]:
    pending_receipts = db.scalars(
        select(ReceiptDoc)
        .where(ReceiptDoc.status == DOC_STATUS_PENDING_SUPPLEMENT)
        .order_by(ReceiptDoc.created_at.asc())
    ).all()
    pending_payments = db.scalars(
        select(PaymentDoc)
        .where(PaymentDoc.status == DOC_STATUS_PENDING_SUPPLEMENT)
        .order_by(PaymentDoc.created_at.asc())
    ).all()
    failed_inbounds = db.scalars(
        select(InboundDoc)
        .where(InboundDoc.status == DOC_STATUS_VALIDATION_FAILED)
        .order_by(InboundDoc.created_at.asc())
    ).all()
    failed_outbounds = db.scalars(
        select(OutboundDoc)
        .where(OutboundDoc.status == DOC_STATUS_VALIDATION_FAILED)
        .order_by(OutboundDoc.created_at.asc())
    ).all()
    qty_done_contracts = db.scalars(
        select(Contract)
        .where(Contract.status == CONTRACT_STATUS_QTY_DONE)
        .order_by(Contract.updated_at.asc())
    ).all()

    contract_nos = _load_contract_no_map(
        db,
        contract_ids={
            *(doc.contract_id for doc in pending_receipts),
            *(doc.contract_id for doc in pending_payments),
            *(doc.contract_id for doc in failed_inbounds),
            *(doc.contract_id for doc in failed_outbounds),
            *(contract.id for contract in qty_done_contracts),
        },
    )

    pending_items = [
        *_serialize_receipt_board_items(pending_receipts, contract_nos),
        *_serialize_payment_board_items(pending_payments, contract_nos),
    ]
    pending_items.sort(key=lambda item: item["created_at"] or "")

    validation_items = [
        *_serialize_inbound_board_items(failed_inbounds, contract_nos),
        *_serialize_outbound_board_items(failed_outbounds, contract_nos),
    ]
    validation_items.sort(key=lambda item: item["created_at"] or "")

    qty_done_items = _serialize_contract_board_items(qty_done_contracts, contract_nos)
    qty_done_items.sort(key=lambda item: item["created_at"] or "")

    total_alert_count = len(pending_items) + len(validation_items) + len(qty_done_items)
    return total_alert_count, pending_items, validation_items, qty_done_items


def _serialize_receipt_board_items(
    docs: list[ReceiptDoc], contract_nos: dict[int, str]
) -> list[dict]:
    return [
        {
            "biz_type": "receipt_doc",
            "biz_id": doc.id,
            "title": f"收款单 {doc.doc_no} 待补录金额",
            "status": doc.status,
            "contract_id": doc.contract_id,
            "contract_no": contract_nos.get(doc.contract_id),
            "related_order_id": doc.sales_order_id,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


def _serialize_payment_board_items(
    docs: list[PaymentDoc], contract_nos: dict[int, str]
) -> list[dict]:
    return [
        {
            "biz_type": "payment_doc",
            "biz_id": doc.id,
            "title": f"付款单 {doc.doc_no} 待补录金额",
            "status": doc.status,
            "contract_id": doc.contract_id,
            "contract_no": contract_nos.get(doc.contract_id),
            "related_order_id": doc.purchase_order_id,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


def _serialize_inbound_board_items(
    docs: list[InboundDoc], contract_nos: dict[int, str]
) -> list[dict]:
    return [
        {
            "biz_type": "inbound_doc",
            "biz_id": doc.id,
            "title": f"入库单 {doc.doc_no} 校验失败",
            "status": doc.status,
            "contract_id": doc.contract_id,
            "contract_no": contract_nos.get(doc.contract_id),
            "related_order_id": doc.purchase_order_id,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


def _serialize_outbound_board_items(
    docs: list[OutboundDoc], contract_nos: dict[int, str]
) -> list[dict]:
    return [
        {
            "biz_type": "outbound_doc",
            "biz_id": doc.id,
            "title": f"出库单 {doc.doc_no} 校验失败",
            "status": doc.status,
            "contract_id": doc.contract_id,
            "contract_no": contract_nos.get(doc.contract_id),
            "related_order_id": doc.sales_order_id,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in docs
    ]


def _serialize_contract_board_items(
    contracts: list[Contract], contract_nos: dict[int, str]
) -> list[dict]:
    return [
        {
            "biz_type": "contract",
            "biz_id": contract.id,
            "title": f"合同 {contract.contract_no} 数量履约完成待关闭",
            "status": contract.status,
            "contract_id": contract.id,
            "contract_no": contract_nos.get(contract.id, contract.contract_no),
            "related_order_id": None,
            "created_at": contract.updated_at.isoformat()
            if contract.updated_at
            else None,
        }
        for contract in contracts
    ]


def _ensure_multi_dim_group_by(group_by: str) -> None:
    if group_by not in ALLOWED_MULTI_DIM_GROUPS:
        raise ReportServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="多维报表分组维度不受支持",
        )


def _resolve_optional_date_window_utc(
    *,
    date_from: date | None,
    date_to: date | None,
) -> tuple[datetime | None, datetime | None]:
    if date_from and date_to and date_to < date_from:
        raise ReportServiceError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="开始日期不能晚于结束日期",
        )
    start_utc: datetime | None = None
    end_utc: datetime | None = None
    if date_from:
        start_utc, _ = _date_range_to_utc(date_from, date_from + timedelta(days=1))
    if date_to:
        _, end_utc = _date_range_to_utc(date_to, date_to + timedelta(days=1))
    return start_utc, end_utc


def _resolve_group_value(
    group_by: str,
    *,
    contract_direction: str | None,
    doc_status: str,
    refund_status: str,
) -> str:
    if group_by == GROUP_BY_CONTRACT_DIRECTION:
        return _label_contract_direction(contract_direction)
    if group_by == GROUP_BY_DOC_STATUS:
        return doc_status
    return refund_status


def _get_or_init_multi_dim_bucket(
    buckets: dict[str, dict[str, Decimal | int | str]],
    *,
    group_by: str,
    group_value: str,
) -> dict[str, Decimal | int | str]:
    if group_value not in buckets:
        buckets[group_value] = {
            "dimension": group_by,
            "receipt_net_amount": Decimal("0.00"),
            "payment_net_amount": Decimal("0.00"),
            "receipt_doc_count": 0,
            "payment_doc_count": 0,
            "pending_supplement_count": 0,
            "refund_pending_review_count": 0,
        }
    return buckets[group_value]


def _passes_multi_dim_filters(
    *,
    contract_direction: str | None,
    doc_status: str,
    refund_status: str,
    created_at: datetime,
    expected_contract_direction: str | None,
    expected_doc_status: str | None,
    expected_refund_status: str | None,
    start_utc: datetime | None,
    end_utc: datetime | None,
) -> bool:
    if (
        expected_contract_direction
        and contract_direction != expected_contract_direction
    ):
        return False
    if expected_doc_status and doc_status != expected_doc_status:
        return False
    if expected_refund_status and refund_status != expected_refund_status:
        return False
    created_at_utc = created_at.astimezone(UTC)
    if start_utc and created_at_utc < start_utc:
        return False
    if end_utc and created_at_utc >= end_utc:
        return False
    return True


def _label_contract_direction(contract_direction: str | None) -> str:
    if contract_direction == CONTRACT_DIRECTION_SALES:
        return "销售"
    if contract_direction == CONTRACT_DIRECTION_PURCHASE:
        return "采购"
    return "未知方向"


def _load_contract_direction_map(db: Session, contract_ids: set[int]) -> dict[int, str]:
    if not contract_ids:
        return {}
    rows = db.scalars(select(Contract).where(Contract.id.in_(contract_ids))).all()
    return {row.id: row.direction for row in rows}


def _load_contract_no_map(db: Session, contract_ids: set[int]) -> dict[int, str]:
    if not contract_ids:
        return {}
    rows = db.scalars(select(Contract).where(Contract.id.in_(contract_ids))).all()
    return {row.id: row.contract_no for row in rows}


def _calculate_fund_net_amount(
    amount_actual: Decimal, refund_amount: Decimal
) -> Decimal:
    return (Decimal(str(amount_actual)) - Decimal(str(refund_amount))).quantize(
        MONEY_PRECISION
    )


def _today_window_utc() -> tuple[datetime, datetime]:
    today_cn = datetime.now(SHANGHAI_TZ).date()
    return _date_range_to_utc(today_cn, today_cn + timedelta(days=1))


def _recent_30_day_window_utc() -> tuple[datetime, datetime]:
    today_cn = datetime.now(SHANGHAI_TZ).date()
    start_day = today_cn - timedelta(days=29)
    end_day = today_cn + timedelta(days=1)
    return _date_range_to_utc(start_day, end_day)


def _date_range_to_utc(start_day: date, end_day: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(start_day, time.min, tzinfo=SHANGHAI_TZ)
    end_local = datetime.combine(end_day, time.min, tzinfo=SHANGHAI_TZ)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)
