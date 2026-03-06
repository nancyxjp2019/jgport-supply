from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, get_current_actor
from app.db.session import get_db
from app.models.inbound_doc import InboundDoc
from app.models.outbound_doc import OutboundDoc
from app.schemas.inventory import (
    InboundDocResponse,
    InboundDocSubmitRequest,
    OutboundDocManualCreateRequest,
    OutboundDocResponse,
    OutboundDocSubmitRequest,
    OutboundDocWarehouseConfirmRequest,
)
from app.services.inventory_service import (
    InventoryServiceError,
    create_manual_outbound_doc,
    create_warehouse_outbound_doc,
    submit_inbound_doc,
    submit_outbound_doc,
)

router = APIRouter(tags=["inventory"])


@router.post("/inbound-docs/{inbound_doc_id}/submit", response_model=InboundDocResponse)
def submit_inbound_doc_route(
    inbound_doc_id: int,
    payload: InboundDocSubmitRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> InboundDocResponse:
    _ensure_inventory_actor(actor)
    try:
        result = submit_inbound_doc(
            db,
            operator_id=actor.user_id,
            inbound_doc_id=inbound_doc_id,
            actual_qty=payload.actual_qty,
            warehouse_id=payload.warehouse_id,
        )
        inbound_doc = db.get(InboundDoc, result.doc_id)
    except InventoryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert inbound_doc is not None
    return _to_inbound_doc_response(inbound_doc, message=result.message)


@router.post("/outbound-docs/warehouse-confirm", response_model=OutboundDocResponse)
def create_system_outbound_doc(
    payload: OutboundDocWarehouseConfirmRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> OutboundDocResponse:
    _ensure_inventory_actor(actor)
    try:
        result = create_warehouse_outbound_doc(
            db,
            operator_id=actor.user_id,
            contract_id=payload.contract_id,
            sales_order_id=payload.sales_order_id,
            source_ticket_no=payload.source_ticket_no,
            actual_qty=payload.actual_qty,
            warehouse_id=payload.warehouse_id,
        )
        outbound_doc = db.get(OutboundDoc, result.doc_id)
    except InventoryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert outbound_doc is not None
    return _to_outbound_doc_response(outbound_doc, message=result.message)


@router.post("/outbound-docs/manual", response_model=OutboundDocResponse)
def create_manual_outbound_doc_route(
    payload: OutboundDocManualCreateRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> OutboundDocResponse:
    _ensure_inventory_actor(actor)
    try:
        result = create_manual_outbound_doc(
            db,
            operator_id=actor.user_id,
            contract_id=payload.contract_id,
            sales_order_id=payload.sales_order_id,
            oil_product_id=payload.oil_product_id,
            manual_ref_no=payload.manual_ref_no,
            actual_qty=payload.actual_qty,
            reason=payload.reason,
        )
        outbound_doc = db.get(OutboundDoc, result.doc_id)
    except InventoryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert outbound_doc is not None
    return _to_outbound_doc_response(outbound_doc, message=result.message)


@router.post("/outbound-docs/{outbound_doc_id}/submit", response_model=OutboundDocResponse)
def submit_outbound_doc_route(
    outbound_doc_id: int,
    payload: OutboundDocSubmitRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> OutboundDocResponse:
    _ensure_inventory_actor(actor)
    try:
        result = submit_outbound_doc(
            db,
            operator_id=actor.user_id,
            outbound_doc_id=outbound_doc_id,
            actual_qty=payload.actual_qty,
            warehouse_id=payload.warehouse_id,
        )
        outbound_doc = db.get(OutboundDoc, result.doc_id)
    except InventoryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert outbound_doc is not None
    return _to_outbound_doc_response(outbound_doc, message=result.message)


def _ensure_inventory_actor(actor: AuthenticatedActor) -> None:
    if (
        actor.role_code in {"operations", "finance", "admin"}
        and actor.company_type == "operator_company"
        and actor.client_type == "admin_web"
    ):
        return
    if (
        actor.role_code == "warehouse"
        and actor.company_type == "warehouse_company"
        and actor.client_type == "miniprogram"
    ):
        return
    raise HTTPException(status_code=403, detail="当前身份无权操作出入库单")


def _to_inbound_doc_response(inbound_doc: InboundDoc, *, message: str) -> InboundDocResponse:
    return InboundDocResponse(
        id=inbound_doc.id,
        doc_no=inbound_doc.doc_no,
        contract_id=inbound_doc.contract_id,
        purchase_order_id=inbound_doc.purchase_order_id,
        oil_product_id=inbound_doc.oil_product_id,
        warehouse_id=inbound_doc.warehouse_id,
        source_type=inbound_doc.source_type,
        actual_qty=inbound_doc.actual_qty,
        status=inbound_doc.status,
        submitted_at=inbound_doc.submitted_at,
        created_at=inbound_doc.created_at,
        message=message,
    )


def _to_outbound_doc_response(outbound_doc: OutboundDoc, *, message: str) -> OutboundDocResponse:
    return OutboundDocResponse(
        id=outbound_doc.id,
        doc_no=outbound_doc.doc_no,
        contract_id=outbound_doc.contract_id,
        sales_order_id=outbound_doc.sales_order_id,
        oil_product_id=outbound_doc.oil_product_id,
        warehouse_id=outbound_doc.warehouse_id,
        source_type=outbound_doc.source_type,
        source_ticket_no=outbound_doc.source_ticket_no,
        manual_ref_no=outbound_doc.manual_ref_no,
        actual_qty=outbound_doc.actual_qty,
        status=outbound_doc.status,
        submitted_at=outbound_doc.submitted_at,
        created_at=outbound_doc.created_at,
        message=message,
    )
