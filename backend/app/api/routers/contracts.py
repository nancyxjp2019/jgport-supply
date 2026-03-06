from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, require_actor
from app.db.session import get_db
from app.models.contract import Contract
from app.schemas.contract import (
    ContractApproveRequest,
    ContractEffectiveTaskResponse,
    ContractGraphResponse,
    ContractManualCloseRequest,
    ContractResponse,
    ContractSubmitRequest,
    PurchaseContractCreateRequest,
    SalesContractCreateRequest,
)
from app.services.contract_close_service import ContractCloseServiceError, manual_close_contract
from app.services.contract_service import (
    CONTRACT_DIRECTION_PURCHASE,
    CONTRACT_DIRECTION_SALES,
    ContractServiceError,
    approve_contract as approve_contract_service,
    create_contract_draft,
    get_contract_or_raise,
    submit_contract_for_approval,
)

router = APIRouter(prefix="/contracts", tags=["contracts"])

contract_write_dependency = require_actor(
    allowed_roles={"finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)
contract_read_dependency = require_actor(
    allowed_roles={"operations", "finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)


@router.post("/purchase", response_model=ContractResponse)
def create_purchase_contract(
    payload: PurchaseContractCreateRequest,
    actor: AuthenticatedActor = Depends(contract_write_dependency),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        result = create_contract_draft(
            db,
            operator_id=actor.user_id,
            contract_no=payload.contract_no,
            direction=CONTRACT_DIRECTION_PURCHASE,
            supplier_id=payload.supplier_id,
            customer_id=None,
            items=payload.items,
        )
        contract = get_contract_or_raise(db, result.contract_id)
    except ContractServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_contract_response(contract, message=result.message)


@router.post("/sales", response_model=ContractResponse)
def create_sales_contract(
    payload: SalesContractCreateRequest,
    actor: AuthenticatedActor = Depends(contract_write_dependency),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        result = create_contract_draft(
            db,
            operator_id=actor.user_id,
            contract_no=payload.contract_no,
            direction=CONTRACT_DIRECTION_SALES,
            supplier_id=None,
            customer_id=payload.customer_id,
            items=payload.items,
        )
        contract = get_contract_or_raise(db, result.contract_id)
    except ContractServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_contract_response(contract, message=result.message)


@router.post("/{contract_id}/submit", response_model=ContractResponse)
def submit_contract(
    contract_id: int,
    payload: ContractSubmitRequest,
    actor: AuthenticatedActor = Depends(contract_write_dependency),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        result = submit_contract_for_approval(
            db,
            contract_id=contract_id,
            operator_id=actor.user_id,
            comment=payload.comment,
        )
        contract = get_contract_or_raise(db, result.contract_id)
    except ContractServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_contract_response(contract, message=result.message)


@router.post("/{contract_id}/approve", response_model=ContractResponse)
def approve_contract(
    contract_id: int,
    payload: ContractApproveRequest,
    actor: AuthenticatedActor = Depends(contract_write_dependency),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        result = approve_contract_service(
            db,
            contract_id=contract_id,
            operator_id=actor.user_id,
            approval_result=payload.approval_result,
            comment=payload.comment,
        )
        contract = get_contract_or_raise(db, result.contract_id)
    except ContractServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_contract_response(
        contract,
        message=result.message,
        generated_task_count=result.generated_task_count,
    )


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract_detail(
    contract_id: int,
    _: AuthenticatedActor = Depends(contract_read_dependency),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        contract = get_contract_or_raise(db, contract_id)
    except ContractServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_contract_response(contract, message="合同详情查询成功")


@router.get("/{contract_id}/graph", response_model=ContractGraphResponse)
def get_contract_graph(
    contract_id: int,
    _: AuthenticatedActor = Depends(contract_read_dependency),
    db: Session = Depends(get_db),
) -> ContractGraphResponse:
    try:
        contract = get_contract_or_raise(db, contract_id)
    except ContractServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return ContractGraphResponse(
        contract_id=contract.id,
        contract_no=contract.contract_no,
        direction=contract.direction,
        status=contract.status,
        downstream_tasks=[
            ContractEffectiveTaskResponse(
                id=task.id,
                target_doc_type=task.target_doc_type,
                status=task.status,
                idempotency_key=task.idempotency_key,
            )
            for task in contract.effective_tasks
        ],
        message="合同图谱查询成功",
    )


@router.post("/{contract_id}/manual-close", response_model=ContractResponse)
def manual_close_contract_route(
    contract_id: int,
    payload: ContractManualCloseRequest,
    actor: AuthenticatedActor = Depends(contract_write_dependency),
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        result = manual_close_contract(
            db,
            contract_id=contract_id,
            operator_id=actor.user_id,
            reason=payload.reason,
            confirm_token=payload.confirm_token,
        )
        contract = get_contract_or_raise(db, result.contract_id)
    except (ContractCloseServiceError, ContractServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_contract_response(contract, message=result.message)


def _to_contract_response(
    contract: Contract,
    *,
    message: str,
    generated_task_count: int | None = None,
) -> ContractResponse:
    return ContractResponse(
        id=contract.id,
        contract_no=contract.contract_no,
        direction=contract.direction,
        status=contract.status,
        supplier_id=contract.supplier_id,
        customer_id=contract.customer_id,
        threshold_release_snapshot=contract.threshold_release_snapshot,
        threshold_over_exec_snapshot=contract.threshold_over_exec_snapshot,
        close_type=contract.close_type,
        closed_by=contract.closed_by,
        closed_at=contract.closed_at,
        manual_close_reason=contract.manual_close_reason,
        manual_close_by=contract.manual_close_by,
        manual_close_at=contract.manual_close_at,
        manual_close_diff_amount=contract.manual_close_diff_amount,
        manual_close_diff_qty_json=contract.manual_close_diff_qty_json,
        submit_comment=contract.submit_comment,
        approval_comment=contract.approval_comment,
        approved_by=contract.approved_by,
        submitted_at=contract.submitted_at,
        approved_at=contract.approved_at,
        items=[
            {
                "id": item.id,
                "oil_product_id": item.oil_product_id,
                "qty_signed": item.qty_signed,
                "unit_price": item.unit_price,
                "qty_in_acc": item.qty_in_acc,
                "qty_out_acc": item.qty_out_acc,
            }
            for item in contract.items
        ],
        generated_task_count=generated_task_count if generated_task_count is not None else len(contract.effective_tasks),
        message=message,
    )
