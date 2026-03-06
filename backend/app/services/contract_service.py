from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.business_audit_log import BusinessAuditLog
from app.models.contract import Contract
from app.models.contract_effective_task import ContractEffectiveTask
from app.models.contract_item import ContractItem
from app.schemas.contract import ContractItemPayload
from app.services.threshold_service import get_active_threshold_snapshot

CONTRACT_DIRECTION_PURCHASE = "purchase"
CONTRACT_DIRECTION_SALES = "sales"

STATUS_DRAFT = "草稿"
STATUS_PENDING_APPROVAL = "待审批"
STATUS_EFFECTIVE = "生效中"

QTY_PRECISION = Decimal("0.001")
PRICE_PRECISION = Decimal("0.01")


@dataclass(frozen=True)
class ContractServiceResult:
    contract_id: int
    message: str
    generated_task_count: int = 0


class ContractServiceError(RuntimeError):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def create_contract_draft(
    db: Session,
    *,
    operator_id: str,
    contract_no: str,
    direction: str,
    supplier_id: str | None,
    customer_id: str | None,
    items: list[ContractItemPayload],
) -> ContractServiceResult:
    if get_active_threshold_snapshot(db) is None:
        raise ContractServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="系统阈值未生效，禁止创建合同",
        )
    if _contract_no_exists(db, contract_no):
        raise ContractServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同编号已存在",
        )

    contract = Contract(
        contract_no=contract_no,
        direction=direction,
        status=STATUS_DRAFT,
        supplier_id=supplier_id,
        customer_id=customer_id,
        created_by=operator_id,
        updated_by=operator_id,
    )
    db.add(contract)
    db.flush()

    for item in items:
        db.add(
            ContractItem(
                contract_id=contract.id,
                oil_product_id=item.oil_product_id,
                qty_signed=normalize_qty(item.qty_signed),
                unit_price=normalize_price(item.unit_price),
            )
        )

    db.flush()
    contract = get_contract_or_raise(db, contract.id)
    db.add(
        BusinessAuditLog(
            event_code="M2-CONTRACT-CREATE",
            biz_type="contract",
            biz_id=f"contract:{contract.id}",
            operator_id=operator_id,
            before_json={},
            after_json=build_contract_snapshot(contract),
            extra_json={"direction": direction},
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ContractServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="合同编号或油品明细存在重复",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise ContractServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="合同创建失败，请稍后重试",
        ) from exc
    return ContractServiceResult(contract_id=contract.id, message=_draft_message(direction))


def submit_contract_for_approval(
    db: Session,
    *,
    contract_id: int,
    operator_id: str,
    comment: str,
) -> ContractServiceResult:
    contract = get_contract_or_raise(db, contract_id)
    if contract.status != STATUS_DRAFT:
        raise ContractServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前合同状态不允许提交审批",
        )

    before_json = build_contract_snapshot(contract)
    contract.status = STATUS_PENDING_APPROVAL
    contract.submit_comment = comment
    contract.submitted_at = datetime.now(timezone.utc)
    contract.updated_by = operator_id
    db.add(
        BusinessAuditLog(
            event_code="M2-CONTRACT-SUBMIT",
            biz_type="contract",
            biz_id=f"contract:{contract.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=build_contract_snapshot(contract),
            extra_json={"comment": comment},
        )
    )
    _commit_or_raise(db, message="合同提交审批失败，请稍后重试")
    return ContractServiceResult(contract_id=contract.id, message="合同已提交审批")


def approve_contract(
    db: Session,
    *,
    contract_id: int,
    operator_id: str,
    approval_result: bool,
    comment: str,
) -> ContractServiceResult:
    contract = get_contract_or_raise(db, contract_id)
    if contract.status != STATUS_PENDING_APPROVAL:
        raise ContractServiceError(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前合同状态不允许审批",
        )

    before_json = build_contract_snapshot(contract)
    generated_task_count = 0

    if approval_result:
        active_threshold = get_active_threshold_snapshot(db)
        if active_threshold is None:
            raise ContractServiceError(
                status_code=status.HTTP_409_CONFLICT,
                detail="系统阈值未生效，禁止审批生效",
            )

        contract.status = STATUS_EFFECTIVE
        contract.threshold_release_snapshot = active_threshold.threshold_release
        contract.threshold_over_exec_snapshot = active_threshold.threshold_over_exec
        contract.approval_comment = comment
        contract.approved_by = operator_id
        contract.approved_at = datetime.now(timezone.utc)
        contract.updated_by = operator_id

        tasks = build_effective_tasks(contract)
        generated_task_count = len(tasks)
        for task in tasks:
            db.add(task)
        event_code = "M2-CONTRACT-APPROVE"
        message = "合同审批通过并已生效"
    else:
        contract.status = STATUS_DRAFT
        contract.approval_comment = comment
        contract.updated_by = operator_id
        event_code = "M2-CONTRACT-REJECT"
        message = "合同已驳回并退回草稿"

    db.add(
        BusinessAuditLog(
            event_code=event_code,
            biz_type="contract",
            biz_id=f"contract:{contract.id}",
            operator_id=operator_id,
            before_json=before_json,
            after_json=build_contract_snapshot(contract),
            extra_json={
                "comment": comment,
                "approval_result": approval_result,
                "generated_task_count": generated_task_count,
            },
        )
    )
    _commit_or_raise(db, message="合同审批处理失败，请稍后重试")
    return ContractServiceResult(
        contract_id=contract.id,
        message=message,
        generated_task_count=generated_task_count,
    )


def get_contract_or_raise(db: Session, contract_id: int) -> Contract:
    statement = (
        select(Contract)
        .options(
            selectinload(Contract.items),
            selectinload(Contract.effective_tasks),
        )
        .where(Contract.id == contract_id)
    )
    contract = db.scalar(statement)
    if contract is None:
        raise ContractServiceError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合同不存在",
        )
    return contract


def normalize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_PRECISION)


def normalize_price(value: Decimal) -> Decimal:
    return value.quantize(PRICE_PRECISION)


def build_contract_snapshot(contract: Contract) -> dict:
    return {
        "id": contract.id,
        "contract_no": contract.contract_no,
        "direction": contract.direction,
        "status": contract.status,
        "supplier_id": contract.supplier_id,
        "customer_id": contract.customer_id,
        "threshold_release_snapshot": _stringify_decimal(contract.threshold_release_snapshot),
        "threshold_over_exec_snapshot": _stringify_decimal(contract.threshold_over_exec_snapshot),
        "items": [build_contract_item_snapshot(item) for item in contract.items],
    }


def build_contract_item_snapshot(item: ContractItem) -> dict:
    return {
        "id": item.id,
        "oil_product_id": item.oil_product_id,
        "qty_signed": str(item.qty_signed),
        "unit_price": str(item.unit_price),
        "qty_in_acc": str(item.qty_in_acc),
        "qty_out_acc": str(item.qty_out_acc),
    }


def build_effective_tasks(contract: Contract) -> list[ContractEffectiveTask]:
    target_doc_types = (
        ["payment_doc", "inbound_doc"]
        if contract.direction == CONTRACT_DIRECTION_PURCHASE
        else ["receipt_doc"]
    )
    tasks: list[ContractEffectiveTask] = []
    for target_doc_type in target_doc_types:
        tasks.append(
            ContractEffectiveTask(
                contract_id=contract.id,
                target_doc_type=target_doc_type,
                status="待处理",
                idempotency_key=f"{contract.direction}_contract_effective:{contract.id}:{target_doc_type}",
                payload_json={
                    "contract_id": contract.id,
                    "contract_no": contract.contract_no,
                    "direction": contract.direction,
                    "target_doc_type": target_doc_type,
                    "items": [build_contract_item_snapshot(item) for item in contract.items],
                    "deposit_doc_type": "DEPOSIT" if target_doc_type in {"payment_doc", "receipt_doc"} else None,
                },
            )
        )
    return tasks


def _contract_no_exists(db: Session, contract_no: str) -> bool:
    statement = select(Contract.id).where(Contract.contract_no == contract_no).limit(1)
    return db.scalar(statement) is not None


def _commit_or_raise(db: Session, *, message: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise ContractServiceError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc


def _stringify_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _draft_message(direction: str) -> str:
    return "采购合同草稿已创建" if direction == CONTRACT_DIRECTION_PURCHASE else "销售合同草稿已创建"
