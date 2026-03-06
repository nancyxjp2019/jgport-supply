from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.business_audit_log import BusinessAuditLog
from app.models.contract import Contract
from app.models.contract_effective_task import ContractEffectiveTask
from app.models.contract_item import ContractItem
from app.models.contract_qty_effect import ContractQtyEffect
from app.models.doc_relation import DocRelation
from app.models.inbound_doc import InboundDoc
from app.models.outbound_doc import OutboundDoc
from app.models.sales_order import SalesOrder
from app.services.contract_close_service import evaluate_contract_closure

QTY_PRECISION = Decimal("0.001")

STATUS_DRAFT = "草稿"
STATUS_PENDING_SUBMIT = "待提交"
STATUS_VALIDATION_FAILED = "校验失败"
STATUS_POSTED = "已过账"
STATUS_TERMINATED = "已终止"
STATUS_CONTRACT_EFFECTIVE = "生效中"
STATUS_CONTRACT_QTY_DONE = "数量履约完成"
STATUS_SALES_ORDER_DERIVED = "已衍生采购订单"
STATUS_SALES_ORDER_EXECUTING = "执行中"
TASK_STATUS_PENDING = "待处理"
TASK_STATUS_GENERATED = "已生成"

SOURCE_TYPE_AUTO_CONTRACT = "AUTO_CONTRACT"
SOURCE_TYPE_SYSTEM = "SYSTEM"
SOURCE_TYPE_MANUAL = "MANUAL"

EFFECT_TYPE_IN = "IN"
EFFECT_TYPE_OUT = "OUT"

RELATION_GENERATES = "GENERATES"
RELATION_BINDS = "BINDS"


@dataclass(frozen=True)
class InventoryServiceResult:
    doc_id: int
    message: str


class InventoryServiceError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def materialize_contract_effective_inbound_docs(
    db: Session,
    *,
    operator_id: str,
    tasks: list[ContractEffectiveTask],
) -> None:
    for task in tasks:
        if task.target_doc_type != "inbound_doc" or task.status != TASK_STATUS_PENDING:
            continue

        payload = task.payload_json
        contract_id = int(payload["contract_id"])
        items = payload.get("items", [])
        for item in items:
            oil_product_id = str(item["oil_product_id"])
            idempotency_key = f"{task.idempotency_key}:{oil_product_id}"
            existing_doc = _get_inbound_doc_by_idempotency_key(db, idempotency_key)
            if existing_doc is not None:
                continue
            inbound_doc = InboundDoc(
                doc_no=_generate_doc_no("INB"),
                contract_id=contract_id,
                purchase_order_id=None,
                oil_product_id=oil_product_id,
                warehouse_id=None,
                source_type=SOURCE_TYPE_AUTO_CONTRACT,
                idempotency_key=idempotency_key,
                actual_qty=Decimal("0.000"),
                status=STATUS_DRAFT,
                created_by=operator_id,
                updated_by=operator_id,
            )
            db.add(inbound_doc)
            db.flush()
            _ensure_doc_relation(
                db,
                source_doc_type="contract",
                source_doc_id=contract_id,
                target_doc_type="inbound_doc",
                target_doc_id=inbound_doc.id,
                relation_type=RELATION_GENERATES,
            )
            _write_inventory_audit(
                db,
                event_code="M5-INBOUND-DOC-GENERATE",
                biz_type="inbound_doc",
                biz_id=f"inbound_doc:{inbound_doc.id}",
                operator_id=operator_id,
                after_json=_build_inbound_snapshot(inbound_doc),
                extra_json={"task_id": task.id, "oil_product_id": oil_product_id},
            )

        task.status = TASK_STATUS_GENERATED


def create_warehouse_outbound_doc(
    db: Session,
    *,
    operator_id: str,
    contract_id: int,
    sales_order_id: int,
    source_ticket_no: str,
    actual_qty: Decimal,
    warehouse_id: str,
) -> InventoryServiceResult:
    sales_contract = _get_contract_with_items_or_raise(db, contract_id)
    _validate_sales_contract_for_outbound(sales_contract)
    sales_order = _get_sales_order_or_raise(db, sales_order_id)
    _ensure_sales_order_matches_contract(sales_order, contract_id)
    _ensure_sales_order_ready_for_outbound(sales_order)

    idempotency_key = f"warehouse_outbound:{contract_id}:{sales_order_id}:{source_ticket_no.strip()}"
    existing_doc = _get_outbound_doc_by_idempotency_key(db, idempotency_key)
    if existing_doc is not None:
        return InventoryServiceResult(doc_id=existing_doc.id, message="仓库正常流程出库单已存在")

    outbound_doc = OutboundDoc(
        doc_no=_generate_doc_no("OUT"),
        contract_id=contract_id,
        sales_order_id=sales_order_id,
        oil_product_id=sales_order.oil_product_id,
        warehouse_id=warehouse_id.strip(),
        source_type=SOURCE_TYPE_SYSTEM,
        source_ticket_no=source_ticket_no.strip(),
        manual_ref_no=None,
        idempotency_key=idempotency_key,
        actual_qty=normalize_qty(actual_qty),
        status=STATUS_PENDING_SUBMIT,
        created_by=operator_id,
        updated_by=operator_id,
    )
    db.add(outbound_doc)
    db.flush()
    _ensure_doc_relation(
        db,
        source_doc_type="contract",
        source_doc_id=contract_id,
        target_doc_type="outbound_doc",
        target_doc_id=outbound_doc.id,
        relation_type=RELATION_GENERATES,
    )
    _ensure_doc_relation(
        db,
        source_doc_type="sales_order",
        source_doc_id=sales_order_id,
        target_doc_type="outbound_doc",
        target_doc_id=outbound_doc.id,
        relation_type=RELATION_GENERATES,
    )
    _write_inventory_audit(
        db,
        event_code="M5-OUTBOUND-DOC-CREATE-SYSTEM",
        biz_type="outbound_doc",
        biz_id=f"outbound_doc:{outbound_doc.id}",
        operator_id=operator_id,
        after_json=_build_outbound_snapshot(outbound_doc),
        extra_json={"source_ticket_no": outbound_doc.source_ticket_no},
    )
    _commit_or_raise(db, message="创建仓库正常流程出库单失败，请稍后重试")
    return InventoryServiceResult(doc_id=outbound_doc.id, message="仓库正常流程出库单已生成")


def create_manual_outbound_doc(
    db: Session,
    *,
    operator_id: str,
    contract_id: int,
    sales_order_id: int,
    oil_product_id: str,
    manual_ref_no: str,
    actual_qty: Decimal,
    reason: str,
) -> InventoryServiceResult:
    sales_contract = _get_contract_with_items_or_raise(db, contract_id)
    _validate_sales_contract_for_outbound(sales_contract)
    sales_order = _get_sales_order_or_raise(db, sales_order_id)
    _ensure_sales_order_matches_contract(sales_order, contract_id)
    _ensure_sales_order_ready_for_outbound(sales_order)
    if sales_order.oil_product_id != oil_product_id:
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="销售订单与油品不匹配，禁止补录出库单",
        )
    if _manual_outbound_exists(db, contract_id=contract_id, oil_product_id=oil_product_id, manual_ref_no=manual_ref_no.strip()):
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="手工回执号已存在，禁止重复补录出库单",
        )

    outbound_doc = OutboundDoc(
        doc_no=_generate_doc_no("OUT"),
        contract_id=contract_id,
        sales_order_id=sales_order_id,
        oil_product_id=oil_product_id,
        warehouse_id=None,
        source_type=SOURCE_TYPE_MANUAL,
        source_ticket_no=None,
        manual_ref_no=manual_ref_no.strip(),
        idempotency_key=f"manual_outbound:{contract_id}:{oil_product_id}:{manual_ref_no.strip()}",
        actual_qty=normalize_qty(actual_qty),
        status=STATUS_PENDING_SUBMIT,
        created_by=operator_id,
        updated_by=operator_id,
    )
    db.add(outbound_doc)
    db.flush()
    _ensure_doc_relation(
        db,
        source_doc_type="contract",
        source_doc_id=contract_id,
        target_doc_type="outbound_doc",
        target_doc_id=outbound_doc.id,
        relation_type=RELATION_BINDS,
    )
    _ensure_doc_relation(
        db,
        source_doc_type="sales_order",
        source_doc_id=sales_order_id,
        target_doc_type="outbound_doc",
        target_doc_id=outbound_doc.id,
        relation_type=RELATION_BINDS,
    )
    _write_inventory_audit(
        db,
        event_code="M5-OUTBOUND-DOC-CREATE-MANUAL",
        biz_type="outbound_doc",
        biz_id=f"outbound_doc:{outbound_doc.id}",
        operator_id=operator_id,
        after_json=_build_outbound_snapshot(outbound_doc),
        extra_json={"manual_ref_no": outbound_doc.manual_ref_no, "reason": reason.strip()},
    )
    _commit_or_raise(db, message="补录出库单失败，请稍后重试")
    return InventoryServiceResult(doc_id=outbound_doc.id, message="手工补录出库单已创建")


def submit_inbound_doc(
    db: Session,
    *,
    operator_id: str,
    inbound_doc_id: int,
    actual_qty: Decimal,
    warehouse_id: str,
) -> InventoryServiceResult:
    inbound_doc = _get_inbound_doc_or_raise(db, inbound_doc_id)
    if inbound_doc.status == STATUS_POSTED:
        return InventoryServiceResult(doc_id=inbound_doc.id, message="入库单已过账，无需重复提交")
    if inbound_doc.status not in {STATUS_DRAFT, STATUS_PENDING_SUBMIT, STATUS_VALIDATION_FAILED}:
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前入库单状态不允许提交",
        )

    contract = _get_contract_with_items_or_raise(db, inbound_doc.contract_id)
    _validate_purchase_contract_for_inbound(contract)
    contract_item = _get_contract_item_or_raise(contract, inbound_doc.oil_product_id)
    before_json = _build_inbound_snapshot(inbound_doc)
    inbound_doc.actual_qty = normalize_qty(actual_qty)
    inbound_doc.warehouse_id = warehouse_id.strip()
    inbound_doc.updated_by = operator_id
    inbound_doc.status = STATUS_PENDING_SUBMIT

    if _contract_qty_done(contract):
        inbound_doc.status = STATUS_TERMINATED
        _write_inventory_audit(
            db,
            event_code="M5-INBOUND-DOC-TERMINATE",
            biz_type="inbound_doc",
            biz_id=f"inbound_doc:{inbound_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_inbound_snapshot(inbound_doc),
            extra_json={"blocked_code": "BIZ-CONTRACT-QTY-DONE-001"},
        )
        _commit_or_raise(db, message="提交入库单失败，请稍后重试")
        return InventoryServiceResult(doc_id=inbound_doc.id, message="合同已数量履约完成，入库单已终止")

    threshold = _get_over_exec_threshold_or_raise(contract)
    projected_qty = normalize_qty(contract_item.qty_in_acc + inbound_doc.actual_qty)
    max_qty = normalize_qty(contract_item.qty_signed * threshold)
    if projected_qty > max_qty:
        inbound_doc.status = STATUS_VALIDATION_FAILED
        _write_inventory_audit(
            db,
            event_code="M5-INBOUND-DOC-BLOCK-THRESHOLD",
            biz_type="inbound_doc",
            biz_id=f"inbound_doc:{inbound_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_inbound_snapshot(inbound_doc),
            extra_json={
                "blocked_code": "BIZ-CONTRACT-THRESHOLD-001",
                "projected_qty": str(projected_qty),
                "max_qty": str(max_qty),
            },
        )
        _commit_or_raise(db, message="提交入库单失败，请稍后重试")
        return InventoryServiceResult(doc_id=inbound_doc.id, message="入库数量超过合同上限阈值，已转校验失败")

    before_contract_json = _build_contract_snapshot(contract)
    effect_applied = _apply_qty_effect(
        db,
        contract_item=contract_item,
        doc_type="inbound_doc",
        doc_id=inbound_doc.id,
        effect_type=EFFECT_TYPE_IN,
        effect_qty=inbound_doc.actual_qty,
    )
    inbound_doc.status = STATUS_POSTED
    inbound_doc.submitted_by = operator_id
    inbound_doc.submitted_at = datetime.now(timezone.utc)
    _finalize_contract_qty_state(contract)
    _write_inventory_audit(
        db,
        event_code="M5-INBOUND-DOC-SUBMIT",
        biz_type="inbound_doc",
        biz_id=f"inbound_doc:{inbound_doc.id}",
        operator_id=operator_id,
        before_json=before_json,
        after_json=_build_inbound_snapshot(inbound_doc),
        extra_json={"effect_applied": effect_applied},
    )
    _write_contract_qty_done_audit_if_needed(
        db,
        contract=contract,
        operator_id=operator_id,
        before_json=before_contract_json,
    )
    close_result = evaluate_contract_closure(
        db,
        contract_id=contract.id,
        operator_id=operator_id,
        trigger_code="INBOUND_DOC_POSTED",
    )
    _commit_or_raise(db, message="提交入库单失败，请稍后重试")
    if close_result.closed:
        return InventoryServiceResult(doc_id=inbound_doc.id, message="入库单已过账，合同已自动关闭")
    if effect_applied:
        message = "入库单已过账并计入履约数量"
    else:
        message = "入库单已过账，重复履约累计已幂等跳过"
    return InventoryServiceResult(doc_id=inbound_doc.id, message=message)


def submit_outbound_doc(
    db: Session,
    *,
    operator_id: str,
    outbound_doc_id: int,
    actual_qty: Decimal,
    warehouse_id: str,
) -> InventoryServiceResult:
    outbound_doc = _get_outbound_doc_or_raise(db, outbound_doc_id)
    if outbound_doc.status == STATUS_POSTED:
        return InventoryServiceResult(doc_id=outbound_doc.id, message="出库单已过账，无需重复提交")
    if outbound_doc.status not in {STATUS_PENDING_SUBMIT, STATUS_VALIDATION_FAILED, STATUS_DRAFT}:
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前出库单状态不允许提交",
        )

    contract = _get_contract_with_items_or_raise(db, outbound_doc.contract_id)
    _validate_sales_contract_for_outbound(contract)
    contract_item = _get_contract_item_or_raise(contract, outbound_doc.oil_product_id)
    before_json = _build_outbound_snapshot(outbound_doc)
    outbound_doc.actual_qty = normalize_qty(actual_qty)
    outbound_doc.warehouse_id = warehouse_id.strip()
    outbound_doc.updated_by = operator_id
    outbound_doc.status = STATUS_PENDING_SUBMIT

    if _contract_qty_done(contract):
        outbound_doc.status = STATUS_TERMINATED
        _write_inventory_audit(
            db,
            event_code="M5-OUTBOUND-DOC-TERMINATE",
            biz_type="outbound_doc",
            biz_id=f"outbound_doc:{outbound_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_outbound_snapshot(outbound_doc),
            extra_json={"blocked_code": "BIZ-CONTRACT-QTY-DONE-001"},
        )
        _commit_or_raise(db, message="提交出库单失败，请稍后重试")
        return InventoryServiceResult(doc_id=outbound_doc.id, message="合同已数量履约完成，出库单已终止")

    threshold = _get_over_exec_threshold_or_raise(contract)
    projected_qty = normalize_qty(contract_item.qty_out_acc + outbound_doc.actual_qty)
    max_qty = normalize_qty(contract_item.qty_signed * threshold)
    if projected_qty > max_qty:
        outbound_doc.status = STATUS_VALIDATION_FAILED
        _write_inventory_audit(
            db,
            event_code="M5-OUTBOUND-DOC-BLOCK-THRESHOLD",
            biz_type="outbound_doc",
            biz_id=f"outbound_doc:{outbound_doc.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=_build_outbound_snapshot(outbound_doc),
            extra_json={
                "blocked_code": "BIZ-CONTRACT-THRESHOLD-001",
                "projected_qty": str(projected_qty),
                "max_qty": str(max_qty),
            },
        )
        _commit_or_raise(db, message="提交出库单失败，请稍后重试")
        return InventoryServiceResult(doc_id=outbound_doc.id, message="出库数量超过合同上限阈值，已转校验失败")

    before_contract_json = _build_contract_snapshot(contract)
    effect_applied = _apply_qty_effect(
        db,
        contract_item=contract_item,
        doc_type="outbound_doc",
        doc_id=outbound_doc.id,
        effect_type=EFFECT_TYPE_OUT,
        effect_qty=outbound_doc.actual_qty,
    )
    outbound_doc.status = STATUS_POSTED
    outbound_doc.submitted_by = operator_id
    outbound_doc.submitted_at = datetime.now(timezone.utc)
    _finalize_contract_qty_state(contract)
    _write_inventory_audit(
        db,
        event_code="M5-OUTBOUND-DOC-SUBMIT",
        biz_type="outbound_doc",
        biz_id=f"outbound_doc:{outbound_doc.id}",
        operator_id=operator_id,
        before_json=before_json,
        after_json=_build_outbound_snapshot(outbound_doc),
        extra_json={"effect_applied": effect_applied},
    )
    _write_contract_qty_done_audit_if_needed(
        db,
        contract=contract,
        operator_id=operator_id,
        before_json=before_contract_json,
    )
    close_result = evaluate_contract_closure(
        db,
        contract_id=contract.id,
        operator_id=operator_id,
        trigger_code="OUTBOUND_DOC_POSTED",
    )
    _commit_or_raise(db, message="提交出库单失败，请稍后重试")
    if close_result.closed:
        return InventoryServiceResult(doc_id=outbound_doc.id, message="出库单已过账，合同已自动关闭")
    if effect_applied:
        message = "出库单已过账并计入履约数量"
    else:
        message = "出库单已过账，重复履约累计已幂等跳过"
    return InventoryServiceResult(doc_id=outbound_doc.id, message=message)


def normalize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_PRECISION)


def _apply_qty_effect(
    db: Session,
    *,
    contract_item: ContractItem,
    doc_type: str,
    doc_id: int,
    effect_type: str,
    effect_qty: Decimal,
) -> bool:
    idempotency_key = f"qty_effect:{doc_type}:{doc_id}:{effect_type}"
    existing_effect = db.scalar(select(ContractQtyEffect.id).where(ContractQtyEffect.idempotency_key == idempotency_key))
    if existing_effect is not None:
        return False

    db.add(
        ContractQtyEffect(
            contract_item_id=contract_item.id,
            doc_type=doc_type,
            doc_id=doc_id,
            effect_type=effect_type,
            effect_qty=effect_qty,
            idempotency_key=idempotency_key,
        )
    )
    if effect_type == EFFECT_TYPE_IN:
        contract_item.qty_in_acc = normalize_qty(contract_item.qty_in_acc + effect_qty)
    else:
        contract_item.qty_out_acc = normalize_qty(contract_item.qty_out_acc + effect_qty)
    return True


def _finalize_contract_qty_state(contract: Contract) -> None:
    if _contract_qty_done(contract):
        contract.status = STATUS_CONTRACT_QTY_DONE


def _contract_qty_done(contract: Contract) -> bool:
    if contract.direction == "purchase":
        return all(item.qty_in_acc >= item.qty_signed for item in contract.items)
    return all(item.qty_out_acc >= item.qty_signed for item in contract.items)


def _validate_purchase_contract_for_inbound(contract: Contract) -> None:
    if contract.direction != "purchase":
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前合同不是采购合同，禁止生成或提交入库单",
        )
    if contract.status not in {STATUS_CONTRACT_EFFECTIVE, STATUS_CONTRACT_QTY_DONE}:
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="采购合同未生效，禁止操作入库单",
        )


def _validate_sales_contract_for_outbound(contract: Contract) -> None:
    if contract.direction != "sales":
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前合同不是销售合同，禁止生成或提交出库单",
        )
    if contract.status not in {STATUS_CONTRACT_EFFECTIVE, STATUS_CONTRACT_QTY_DONE}:
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="销售合同未生效，禁止操作出库单",
        )


def _get_contract_with_items_or_raise(db: Session, contract_id: int) -> Contract:
    statement = select(Contract).options(selectinload(Contract.items)).where(Contract.id == contract_id)
    contract = db.scalar(statement)
    if contract is None:
        raise InventoryServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联合同不存在",
        )
    return contract


def _get_contract_item_or_raise(contract: Contract, oil_product_id: str) -> ContractItem:
    for item in contract.items:
        if item.oil_product_id == oil_product_id:
            return item
    raise InventoryServiceError(
        status_code=status.HTTP_409_CONFLICT,
        detail="关联合同缺少当前油品明细",
    )


def _get_sales_order_or_raise(db: Session, sales_order_id: int) -> SalesOrder:
    sales_order = db.get(SalesOrder, sales_order_id)
    if sales_order is None:
        raise InventoryServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="销售订单不存在",
        )
    return sales_order


def _ensure_sales_order_matches_contract(sales_order: SalesOrder, contract_id: int) -> None:
    if sales_order.sales_contract_id != contract_id:
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="销售合同与销售订单不匹配，禁止生成出库单",
        )


def _ensure_sales_order_ready_for_outbound(sales_order: SalesOrder) -> None:
    if sales_order.status in {STATUS_SALES_ORDER_DERIVED, STATUS_SALES_ORDER_EXECUTING}:
        return
    raise InventoryServiceError(
        status_code=status.HTTP_409_CONFLICT,
        detail="销售订单未进入执行阶段，禁止生成出库单",
    )


def _get_inbound_doc_or_raise(db: Session, inbound_doc_id: int) -> InboundDoc:
    inbound_doc = db.get(InboundDoc, inbound_doc_id)
    if inbound_doc is None:
        raise InventoryServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="入库单不存在",
        )
    return inbound_doc


def _get_outbound_doc_or_raise(db: Session, outbound_doc_id: int) -> OutboundDoc:
    outbound_doc = db.get(OutboundDoc, outbound_doc_id)
    if outbound_doc is None:
        raise InventoryServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="出库单不存在",
        )
    return outbound_doc


def _get_inbound_doc_by_idempotency_key(db: Session, idempotency_key: str) -> InboundDoc | None:
    statement = select(InboundDoc).where(InboundDoc.idempotency_key == idempotency_key)
    return db.scalar(statement)


def _get_outbound_doc_by_idempotency_key(db: Session, idempotency_key: str) -> OutboundDoc | None:
    statement = select(OutboundDoc).where(OutboundDoc.idempotency_key == idempotency_key)
    return db.scalar(statement)


def _manual_outbound_exists(db: Session, *, contract_id: int, oil_product_id: str, manual_ref_no: str) -> bool:
    statement = select(OutboundDoc.id).where(
        OutboundDoc.contract_id == contract_id,
        OutboundDoc.oil_product_id == oil_product_id,
        OutboundDoc.manual_ref_no == manual_ref_no,
    )
    return db.scalar(statement) is not None


def _get_over_exec_threshold_or_raise(contract: Contract) -> Decimal:
    if contract.threshold_over_exec_snapshot is None:
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同缺少超量履约阈值快照，禁止提交出入库单",
        )
    return Decimal(str(contract.threshold_over_exec_snapshot))


def _ensure_doc_relation(
    db: Session,
    *,
    source_doc_type: str,
    source_doc_id: int,
    target_doc_type: str,
    target_doc_id: int,
    relation_type: str,
) -> None:
    statement = select(DocRelation.id).where(
        DocRelation.source_doc_type == source_doc_type,
        DocRelation.source_doc_id == source_doc_id,
        DocRelation.target_doc_type == target_doc_type,
        DocRelation.target_doc_id == target_doc_id,
        DocRelation.relation_type == relation_type,
    )
    if db.scalar(statement) is not None:
        return
    db.add(
        DocRelation(
            source_doc_type=source_doc_type,
            source_doc_id=source_doc_id,
            target_doc_type=target_doc_type,
            target_doc_id=target_doc_id,
            relation_type=relation_type,
        )
    )


def _write_inventory_audit(
    db: Session,
    *,
    event_code: str,
    biz_type: str,
    biz_id: str,
    operator_id: str,
    after_json: dict,
    extra_json: dict,
    before_json: dict | None = None,
) -> None:
    db.add(
        BusinessAuditLog(
            event_code=event_code,
            biz_type=biz_type,
            biz_id=biz_id,
            operator_id=operator_id,
            before_json=before_json or {},
            after_json=after_json,
            extra_json=extra_json,
        )
    )


def _write_contract_qty_done_audit_if_needed(
    db: Session,
    *,
    contract: Contract,
    operator_id: str,
    before_json: dict,
) -> None:
    if before_json.get("status") == contract.status or contract.status != STATUS_CONTRACT_QTY_DONE:
        return
    _write_inventory_audit(
        db,
        event_code="M5-CONTRACT-QTY-DONE",
        biz_type="contract",
        biz_id=f"contract:{contract.id}",
        operator_id=operator_id,
        before_json=before_json,
        after_json=_build_contract_snapshot(contract),
        extra_json={"direction": contract.direction},
    )


def _build_contract_snapshot(contract: Contract) -> dict:
    return {
        "id": contract.id,
        "contract_no": contract.contract_no,
        "direction": contract.direction,
        "status": contract.status,
        "items": [
            {
                "id": item.id,
                "oil_product_id": item.oil_product_id,
                "qty_signed": str(item.qty_signed),
                "qty_in_acc": str(item.qty_in_acc),
                "qty_out_acc": str(item.qty_out_acc),
            }
            for item in contract.items
        ],
    }


def _build_inbound_snapshot(inbound_doc: InboundDoc) -> dict:
    return {
        "id": inbound_doc.id,
        "doc_no": inbound_doc.doc_no,
        "contract_id": inbound_doc.contract_id,
        "purchase_order_id": inbound_doc.purchase_order_id,
        "oil_product_id": inbound_doc.oil_product_id,
        "warehouse_id": inbound_doc.warehouse_id,
        "source_type": inbound_doc.source_type,
        "actual_qty": str(inbound_doc.actual_qty),
        "status": inbound_doc.status,
        "submitted_by": inbound_doc.submitted_by,
        "submitted_at": inbound_doc.submitted_at.isoformat() if inbound_doc.submitted_at else None,
    }


def _build_outbound_snapshot(outbound_doc: OutboundDoc) -> dict:
    return {
        "id": outbound_doc.id,
        "doc_no": outbound_doc.doc_no,
        "contract_id": outbound_doc.contract_id,
        "sales_order_id": outbound_doc.sales_order_id,
        "oil_product_id": outbound_doc.oil_product_id,
        "warehouse_id": outbound_doc.warehouse_id,
        "source_type": outbound_doc.source_type,
        "source_ticket_no": outbound_doc.source_ticket_no,
        "manual_ref_no": outbound_doc.manual_ref_no,
        "actual_qty": str(outbound_doc.actual_qty),
        "status": outbound_doc.status,
        "submitted_by": outbound_doc.submitted_by,
        "submitted_at": outbound_doc.submitted_at.isoformat() if outbound_doc.submitted_at else None,
    }


def _generate_doc_no(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12].upper()}"


def _commit_or_raise(db: Session, *, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise InventoryServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="出入库单编号、幂等键或履约累计存在重复",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise InventoryServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc
