from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business_log import BusinessLog
from app.models.user import User
from app.models.v5_domain import PurchaseOrderV5, PurchaseOrderV5Status, SalesOrderV5, SalesOrderV5Status
from app.schemas.v5_tracking import V5OrderLogOut


_SALES_LOG_ACTIONS = (
    "V5_SALES_ORDER_CREATE",
    "V5_SALES_ORDER_OPERATOR_REVIEW",
    "V5_SALES_ORDER_FINANCE_REVIEW",
    "V5_SALES_ORDER_REJECT",
    "V5_SALES_ORDER_ABNORMAL_CLOSE",
)

_PURCHASE_LOG_ACTIONS = (
    "V5_PURCHASE_ORDER_CREATE",
    "V5_PURCHASE_ORDER_SUBMIT",
    "V5_PURCHASE_ORDER_SUPPLIER_PAYMENT",
    "V5_PURCHASE_ORDER_SUPPLIER_REVIEW",
    "V5_PURCHASE_ORDER_WAREHOUSE_OUTBOUND",
    "V5_PURCHASE_ORDER_ABNORMAL_CLOSE",
)

_ACTION_NAME_MAP = {
    "V5_SALES_ORDER_CREATE": "销售订单提交",
    "V5_SALES_ORDER_OPERATOR_REVIEW": "销售订单运营审核通过",
    "V5_SALES_ORDER_FINANCE_REVIEW": "销售订单财务确认收款",
    "V5_SALES_ORDER_REJECT": "销售订单管理员驳回",
    "V5_SALES_ORDER_ABNORMAL_CLOSE": "销售订单异常关闭",
    "V5_PURCHASE_ORDER_CREATE": "采购订单自动生成",
    "V5_PURCHASE_ORDER_SUBMIT": "采购订单提交",
    "V5_PURCHASE_ORDER_SUPPLIER_PAYMENT": "采购订单上传付款凭证",
    "V5_PURCHASE_ORDER_SUPPLIER_REVIEW": "采购订单供应商确认通过",
    "V5_PURCHASE_ORDER_WAREHOUSE_OUTBOUND": "采购订单仓库出库完成",
    "V5_PURCHASE_ORDER_ABNORMAL_CLOSE": "采购订单异常关闭",
}

_PROGRESS_NODE_CODES = (
    "SUBMIT",
    "OPERATOR_REVIEW",
    "FINANCE_REVIEW",
    "PURCHASE_EXECUTION",
    "WAREHOUSE_OUTBOUND",
    "COMPLETE",
)

_PROGRESS_NODE_NAMES = {
    "SUBMIT": "提交下单",
    "OPERATOR_REVIEW": "运营审核",
    "FINANCE_REVIEW": "财务确认收款",
    "PURCHASE_EXECUTION": "采购执行",
    "WAREHOUSE_OUTBOUND": "仓库出库",
    "COMPLETE": "订单完成",
}


def _pending_payload() -> dict[str, object | None]:
    return {"status": "PENDING", "finished_at": None, "operator": None}


def _current_payload() -> dict[str, object | None]:
    return {"status": "CURRENT", "finished_at": None, "operator": None}


def _blocked_payload() -> dict[str, object | None]:
    return {"status": "BLOCKED", "finished_at": None, "operator": None}


def _completed_payload(log: BusinessLog | None) -> dict[str, object | None]:
    if log is None:
        return _pending_payload()
    return {"status": "COMPLETED", "finished_at": log.created_at, "operator": log.user_id}


def _abnormal_payload(log: BusinessLog | None) -> dict[str, object | None]:
    if log is None:
        return {"status": "ABNORMAL", "finished_at": None, "operator": None}
    return {"status": "ABNORMAL", "finished_at": log.created_at, "operator": log.user_id}


def _find_first_log(logs: list[BusinessLog], action: str, after_status: str | None = None) -> BusinessLog | None:
    for log in logs:
        if log.action != action:
            continue
        if after_status is not None and log.after_status != after_status:
            continue
        return log
    return None


def _build_user_name_map(db: Session, user_ids: Iterable[int]) -> dict[int, str]:
    normalized_ids = {item for item in user_ids if item}
    if not normalized_ids:
        return {}
    rows = db.scalars(select(User).where(User.id.in_(normalized_ids))).all()
    return {row.id: (row.username or row.display_name or f"用户{row.id}") for row in rows}


def list_sales_order_logs(db: Session, *, sales_order: SalesOrderV5) -> list[V5OrderLogOut]:
    rows = db.scalars(
        select(BusinessLog)
        .where(
            BusinessLog.entity_type == "SALES_ORDER",
            BusinessLog.entity_id == str(sales_order.id),
            BusinessLog.action.in_(_SALES_LOG_ACTIONS),
            BusinessLog.result == "SUCCESS",
        )
        .order_by(BusinessLog.id.desc())
    ).all()
    return _serialize_logs(db, rows)


def list_purchase_order_logs(db: Session, *, purchase_order: PurchaseOrderV5) -> list[V5OrderLogOut]:
    rows = db.scalars(
        select(BusinessLog)
        .where(
            BusinessLog.entity_type == "PURCHASE_ORDER",
            BusinessLog.entity_id == str(purchase_order.id),
            BusinessLog.action.in_(_PURCHASE_LOG_ACTIONS),
            BusinessLog.result == "SUCCESS",
        )
        .order_by(BusinessLog.id.desc())
    ).all()
    return _serialize_logs(db, rows)


def _serialize_logs(db: Session, rows: list[BusinessLog]) -> list[V5OrderLogOut]:
    user_name_map = _build_user_name_map(db, [row.user_id for row in rows if row.user_id is not None])
    return [
        V5OrderLogOut(
            id=row.id,
            entity_type=row.entity_type or "",
            entity_id=row.entity_id or "",
            action=row.action,
            action_name=_ACTION_NAME_MAP.get(row.action, row.action),
            operator_user_id=row.user_id,
            operator_name=user_name_map.get(row.user_id) if row.user_id is not None else None,
            role=row.role,
            before_status=row.before_status,
            after_status=row.after_status,
            reason=row.reason,
            detail_json=row.detail_json,
            created_at=row.created_at,
        )
        for row in rows
    ]


def build_sales_order_progress(db: Session, *, sales_order: SalesOrderV5) -> list[dict[str, object | None]]:
    sales_logs = db.scalars(
        select(BusinessLog)
        .where(
            BusinessLog.entity_type == "SALES_ORDER",
            BusinessLog.entity_id == str(sales_order.id),
            BusinessLog.action.in_(_SALES_LOG_ACTIONS),
            BusinessLog.result == "SUCCESS",
        )
        .order_by(BusinessLog.id.asc())
    ).all()
    purchase_order = db.scalar(select(PurchaseOrderV5).where(PurchaseOrderV5.sales_order_id == sales_order.id))
    purchase_logs: list[BusinessLog] = []
    if purchase_order is not None:
        purchase_logs = db.scalars(
            select(BusinessLog)
            .where(
                BusinessLog.entity_type == "PURCHASE_ORDER",
                BusinessLog.entity_id == str(purchase_order.id),
                BusinessLog.action.in_(_PURCHASE_LOG_ACTIONS),
                BusinessLog.result == "SUCCESS",
            )
            .order_by(BusinessLog.id.asc())
        ).all()

    create_log = _find_first_log(sales_logs, "V5_SALES_ORDER_CREATE")
    operator_log = _find_first_log(sales_logs, "V5_SALES_ORDER_OPERATOR_REVIEW", after_status=SalesOrderV5Status.OPERATOR_APPROVED.value)
    finance_log = _find_first_log(sales_logs, "V5_SALES_ORDER_FINANCE_REVIEW", after_status=SalesOrderV5Status.CUSTOMER_PAYMENT_CONFIRMED.value)
    reject_log = _find_first_log(sales_logs, "V5_SALES_ORDER_REJECT", after_status=SalesOrderV5Status.REJECTED.value)
    sales_abnormal_log = _find_first_log(sales_logs, "V5_SALES_ORDER_ABNORMAL_CLOSE", after_status=SalesOrderV5Status.ABNORMAL_CLOSED.value)
    supplier_review_log = _find_first_log(purchase_logs, "V5_PURCHASE_ORDER_SUPPLIER_REVIEW")
    warehouse_outbound_log = _find_first_log(purchase_logs, "V5_PURCHASE_ORDER_WAREHOUSE_OUTBOUND")
    purchase_abnormal_log = _find_first_log(purchase_logs, "V5_PURCHASE_ORDER_ABNORMAL_CLOSE")
    abnormal_log = sales_abnormal_log or purchase_abnormal_log

    node_state: dict[str, dict[str, object | None]] = {code: _pending_payload() for code in _PROGRESS_NODE_CODES}
    if create_log is not None:
        node_state["SUBMIT"] = _completed_payload(create_log)

    if sales_order.status == SalesOrderV5Status.SUBMITTED:
        node_state["OPERATOR_REVIEW"] = _current_payload()
    elif sales_order.status == SalesOrderV5Status.OPERATOR_APPROVED:
        node_state["OPERATOR_REVIEW"] = _completed_payload(operator_log)
        node_state["FINANCE_REVIEW"] = _current_payload()
    elif sales_order.status == SalesOrderV5Status.CUSTOMER_PAYMENT_CONFIRMED:
        node_state["OPERATOR_REVIEW"] = _completed_payload(operator_log)
        node_state["FINANCE_REVIEW"] = _completed_payload(finance_log)
        node_state["PURCHASE_EXECUTION"] = _current_payload()
    elif sales_order.status == SalesOrderV5Status.READY_FOR_OUTBOUND:
        node_state["OPERATOR_REVIEW"] = _completed_payload(operator_log)
        node_state["FINANCE_REVIEW"] = _completed_payload(finance_log)
        node_state["PURCHASE_EXECUTION"] = _completed_payload(supplier_review_log)
        node_state["WAREHOUSE_OUTBOUND"] = _current_payload()
    elif sales_order.status == SalesOrderV5Status.COMPLETED:
        node_state["OPERATOR_REVIEW"] = _completed_payload(operator_log)
        node_state["FINANCE_REVIEW"] = _completed_payload(finance_log)
        node_state["PURCHASE_EXECUTION"] = _completed_payload(supplier_review_log)
        node_state["WAREHOUSE_OUTBOUND"] = _completed_payload(warehouse_outbound_log)
        node_state["COMPLETE"] = _completed_payload(warehouse_outbound_log)
    elif sales_order.status == SalesOrderV5Status.REJECTED:
        if reject_log and reject_log.before_status == SalesOrderV5Status.OPERATOR_APPROVED.value:
            node_state["OPERATOR_REVIEW"] = _completed_payload(operator_log)
            node_state["FINANCE_REVIEW"] = _abnormal_payload(reject_log)
        else:
            node_state["OPERATOR_REVIEW"] = _abnormal_payload(reject_log)
            node_state["FINANCE_REVIEW"] = _blocked_payload()
        node_state["PURCHASE_EXECUTION"] = _blocked_payload()
        node_state["WAREHOUSE_OUTBOUND"] = _blocked_payload()
        node_state["COMPLETE"] = _blocked_payload()
    elif sales_order.status == SalesOrderV5Status.ABNORMAL_CLOSED:
        if operator_log is not None:
            node_state["OPERATOR_REVIEW"] = _completed_payload(operator_log)
        if finance_log is not None:
            node_state["FINANCE_REVIEW"] = _completed_payload(finance_log)
        abnormal_before_status = abnormal_log.before_status if abnormal_log is not None else None
        if abnormal_before_status in (
            SalesOrderV5Status.READY_FOR_OUTBOUND.value,
            PurchaseOrderV5Status.WAREHOUSE_PENDING.value,
        ):
            node_state["PURCHASE_EXECUTION"] = _completed_payload(supplier_review_log)
            node_state["WAREHOUSE_OUTBOUND"] = _abnormal_payload(abnormal_log)
            node_state["COMPLETE"] = _blocked_payload()
        else:
            if finance_log is not None:
                node_state["PURCHASE_EXECUTION"] = _abnormal_payload(abnormal_log)
            elif operator_log is not None:
                node_state["FINANCE_REVIEW"] = _abnormal_payload(abnormal_log)
            else:
                node_state["OPERATOR_REVIEW"] = _abnormal_payload(abnormal_log)
            node_state["WAREHOUSE_OUTBOUND"] = _blocked_payload()
            node_state["COMPLETE"] = _blocked_payload()

    user_name_map = _build_user_name_map(
        db,
        [
            item["operator"]
            for item in node_state.values()
            if isinstance(item.get("operator"), int)
        ],
    )
    block_reason = sales_order.closed_reason

    return [
        {
            "node_code": code,
            "node_name": _PROGRESS_NODE_NAMES[code],
            "status": node_state[code]["status"],
            "operator": user_name_map.get(node_state[code]["operator"]) if isinstance(node_state[code]["operator"], int) else None,
            "finished_at": node_state[code]["finished_at"],
            "block_reason": block_reason,
        }
        for code in _PROGRESS_NODE_CODES
    ]
