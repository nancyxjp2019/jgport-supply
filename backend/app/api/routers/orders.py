from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import AuthenticatedActor, get_current_actor, require_actor
from app.models.contract import Contract
from app.db.session import get_db
from app.models.purchase_order import PurchaseOrder
from app.models.sales_order import SalesOrder
from app.schemas.order import (
    AvailableSalesContractItemResponse,
    AvailableSalesContractListResponse,
    AvailableSalesContractResponse,
    PurchaseOrderResponse,
    PurchaseOrderListItemResponse,
    PurchaseOrderListResponse,
    SupplierPurchaseOrderConfirmDeliveryRequest,
    SupplierPurchaseOrderAttachmentCreateRequest,
    SupplierPurchaseOrderAttachmentListItemResponse,
    SupplierPurchaseOrderAttachmentListResponse,
    SupplierPurchaseOrderAttachmentResponse,
    SupplierPurchaseOrderResponse,
    SalesOrderListItemResponse,
    SalesOrderListResponse,
    SalesOrderCreateRequest,
    SalesOrderDerivativeTaskResponse,
    SalesOrderFinanceApproveRequest,
    SalesOrderOpsApproveRequest,
    SalesOrderResponse,
    SalesOrderSubmitRequest,
    SalesOrderUpdateRequest,
)
from app.services.order_service import (
    OrderServiceError,
    confirm_supplier_purchase_order_delivery,
    create_sales_order_draft,
    create_supplier_purchase_order_attachment,
    finance_approve_sales_order,
    get_sales_order_detail_or_raise,
    get_purchase_order_or_raise,
    list_supplier_purchase_orders,
    list_supplier_purchase_order_attachments,
    get_sales_order_or_raise,
    list_available_sales_contracts,
    list_sales_orders,
    ops_approve_sales_order,
    submit_sales_order,
    update_sales_order,
)

router = APIRouter(tags=["orders"])

ops_actor_dependency = require_actor(
    allowed_roles={"operations", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)
finance_actor_dependency = require_actor(
    allowed_roles={"finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)
purchase_order_reader_dependency = require_actor(
    allowed_roles={"operations", "finance", "admin"},
    allowed_client_types={"admin_web"},
    allowed_company_types={"operator_company"},
)
supplier_purchase_order_reader_dependency = require_actor(
    allowed_roles={"supplier"},
    allowed_client_types={"miniprogram"},
    allowed_company_types={"supplier_company"},
)


@router.post("/sales-orders", response_model=SalesOrderResponse)
def create_sales_order(
    payload: SalesOrderCreateRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> SalesOrderResponse:
    required_customer_company_id = _resolve_sales_order_creator_scope(actor)
    try:
        result = create_sales_order_draft(
            db,
            operator_id=actor.user_id,
            required_customer_company_id=required_customer_company_id,
            sales_contract_id=payload.sales_contract_id,
            oil_product_id=payload.oil_product_id,
            qty=payload.qty,
            unit_price=payload.unit_price,
        )
        sales_order = get_sales_order_or_raise(db, result.sales_order_id)
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_sales_order_response(sales_order, message=result.message)


@router.get(
    "/sales-contracts/available", response_model=AvailableSalesContractListResponse
)
def list_available_sales_contracts_route(
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> AvailableSalesContractListResponse:
    customer_company_id = _resolve_customer_sales_order_scope(actor)
    items = list_available_sales_contracts(
        db,
        customer_company_id=customer_company_id,
    )
    return AvailableSalesContractListResponse(
        items=[_to_available_sales_contract_response(item) for item in items],
        total=len(items),
        message="可选销售合同查询成功",
    )


@router.get("/sales-orders", response_model=SalesOrderListResponse)
def list_sales_orders_route(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=50),
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> SalesOrderListResponse:
    required_customer_company_id = _resolve_sales_order_reader_scope(actor)
    items = list_sales_orders(
        db,
        required_customer_company_id=required_customer_company_id,
        status_filter=status_filter,
        limit=limit,
    )
    return SalesOrderListResponse(
        items=[
            _to_sales_order_list_item_response(
                sales_order, sales_contract_no=sales_contract_no
            )
            for sales_order, sales_contract_no in items
        ],
        total=len(items),
        message="销售订单列表查询成功",
    )


@router.get("/sales-orders/{sales_order_id}", response_model=SalesOrderResponse)
def get_sales_order_detail_route(
    sales_order_id: int,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> SalesOrderResponse:
    required_customer_company_id = _resolve_sales_order_reader_scope(actor)
    try:
        sales_order, sales_contract_no = get_sales_order_detail_or_raise(
            db,
            sales_order_id=sales_order_id,
            required_customer_company_id=required_customer_company_id,
        )
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_sales_order_response(
        sales_order,
        message="销售订单详情查询成功",
        sales_contract_no=sales_contract_no,
    )


@router.put("/sales-orders/{sales_order_id}", response_model=SalesOrderResponse)
def update_sales_order_route(
    sales_order_id: int,
    payload: SalesOrderUpdateRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> SalesOrderResponse:
    required_customer_company_id = _resolve_sales_order_creator_scope(actor)
    try:
        result = update_sales_order(
            db,
            sales_order_id=sales_order_id,
            operator_id=actor.user_id,
            required_customer_company_id=required_customer_company_id,
            oil_product_id=payload.oil_product_id,
            qty=payload.qty,
            unit_price=payload.unit_price,
        )
        sales_order = get_sales_order_or_raise(db, result.sales_order_id)
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_sales_order_response(sales_order, message=result.message)


@router.post("/sales-orders/{sales_order_id}/submit", response_model=SalesOrderResponse)
def submit_sales_order_route(
    sales_order_id: int,
    payload: SalesOrderSubmitRequest,
    actor: AuthenticatedActor = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> SalesOrderResponse:
    required_customer_company_id = _resolve_sales_order_creator_scope(actor)
    try:
        result = submit_sales_order(
            db,
            sales_order_id=sales_order_id,
            operator_id=actor.user_id,
            required_customer_company_id=required_customer_company_id,
            comment=payload.comment,
        )
        sales_order = get_sales_order_or_raise(db, result.sales_order_id)
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_sales_order_response(sales_order, message=result.message)


@router.post(
    "/sales-orders/{sales_order_id}/ops-approve", response_model=SalesOrderResponse
)
def ops_approve_sales_order_route(
    sales_order_id: int,
    payload: SalesOrderOpsApproveRequest,
    actor: AuthenticatedActor = Depends(ops_actor_dependency),
    db: Session = Depends(get_db),
) -> SalesOrderResponse:
    try:
        result = ops_approve_sales_order(
            db,
            sales_order_id=sales_order_id,
            operator_id=actor.user_id,
            result=payload.result,
            comment=payload.comment,
        )
        sales_order = get_sales_order_or_raise(db, result.sales_order_id)
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_sales_order_response(sales_order, message=result.message)


@router.post(
    "/sales-orders/{sales_order_id}/finance-approve", response_model=SalesOrderResponse
)
def finance_approve_sales_order_route(
    sales_order_id: int,
    payload: SalesOrderFinanceApproveRequest,
    actor: AuthenticatedActor = Depends(finance_actor_dependency),
    db: Session = Depends(get_db),
) -> SalesOrderResponse:
    try:
        result = finance_approve_sales_order(
            db,
            sales_order_id=sales_order_id,
            operator_id=actor.user_id,
            result=payload.result,
            purchase_contract_id=payload.purchase_contract_id,
            actual_receipt_amount=payload.actual_receipt_amount,
            actual_pay_amount=payload.actual_pay_amount,
            comment=payload.comment,
        )
        sales_order = get_sales_order_or_raise(db, result.sales_order_id)
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_sales_order_response(
        sales_order,
        message=result.message,
        purchase_order_id=result.purchase_order_id,
        generated_task_count=result.generated_task_count,
    )


@router.get(
    "/purchase-orders/{purchase_order_id}", response_model=PurchaseOrderResponse
)
def get_purchase_order_detail(
    purchase_order_id: int,
    _: AuthenticatedActor = Depends(purchase_order_reader_dependency),
    db: Session = Depends(get_db),
) -> PurchaseOrderResponse:
    try:
        purchase_order = get_purchase_order_or_raise(db, purchase_order_id)
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_purchase_order_response(purchase_order, message="采购订单详情查询成功")


@router.get("/supplier/purchase-orders", response_model=PurchaseOrderListResponse)
def list_supplier_purchase_orders_route(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=50),
    actor: AuthenticatedActor = Depends(supplier_purchase_order_reader_dependency),
    db: Session = Depends(get_db),
) -> PurchaseOrderListResponse:
    supplier_company_id = _resolve_supplier_purchase_order_scope(actor)
    items = list_supplier_purchase_orders(
        db,
        supplier_company_id=supplier_company_id,
        status_filter=status_filter,
        limit=limit,
    )
    return PurchaseOrderListResponse(
        items=[
            _to_purchase_order_list_item_response(
                purchase_order, source_sales_order_no=source_sales_order_no
            )
            for purchase_order, source_sales_order_no in items
        ],
        total=len(items),
        message="供应商采购订单列表查询成功",
    )


@router.get(
    "/supplier/purchase-orders/{purchase_order_id}",
    response_model=SupplierPurchaseOrderResponse,
)
def get_supplier_purchase_order_detail(
    purchase_order_id: int,
    actor: AuthenticatedActor = Depends(supplier_purchase_order_reader_dependency),
    db: Session = Depends(get_db),
) -> SupplierPurchaseOrderResponse:
    supplier_company_id = _resolve_supplier_purchase_order_scope(actor)
    try:
        purchase_order = get_purchase_order_or_raise(
            db,
            purchase_order_id,
            required_supplier_company_id=supplier_company_id,
        )
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_supplier_purchase_order_response(
        purchase_order, message="供应商采购订单详情查询成功"
    )


@router.post(
    "/supplier/purchase-orders/{purchase_order_id}/confirm-delivery",
    response_model=SupplierPurchaseOrderResponse,
)
def confirm_supplier_purchase_order_delivery_route(
    purchase_order_id: int,
    payload: SupplierPurchaseOrderConfirmDeliveryRequest,
    actor: AuthenticatedActor = Depends(supplier_purchase_order_reader_dependency),
    db: Session = Depends(get_db),
) -> SupplierPurchaseOrderResponse:
    supplier_company_id = _resolve_supplier_purchase_order_scope(actor)
    try:
        result = confirm_supplier_purchase_order_delivery(
            db,
            purchase_order_id=purchase_order_id,
            supplier_company_id=supplier_company_id,
            operator_id=actor.user_id,
            comment=payload.comment,
        )
        purchase_order = get_purchase_order_or_raise(
            db,
            purchase_order_id=result.purchase_order_id,
            required_supplier_company_id=supplier_company_id,
        )
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_supplier_purchase_order_response(
        purchase_order,
        message=result.message,
    )


@router.get(
    "/supplier/purchase-orders/{purchase_order_id}/attachments",
    response_model=SupplierPurchaseOrderAttachmentListResponse,
)
def list_supplier_purchase_order_attachments_route(
    purchase_order_id: int,
    actor: AuthenticatedActor = Depends(supplier_purchase_order_reader_dependency),
    db: Session = Depends(get_db),
) -> SupplierPurchaseOrderAttachmentListResponse:
    supplier_company_id = _resolve_supplier_purchase_order_scope(actor)
    try:
        items = list_supplier_purchase_order_attachments(
            db,
            purchase_order_id=purchase_order_id,
            supplier_company_id=supplier_company_id,
        )
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return SupplierPurchaseOrderAttachmentListResponse(
        items=[
            _to_supplier_purchase_order_attachment_list_item(item) for item in items
        ],
        total=len(items),
        message="供应商采购订单附件查询成功",
    )


@router.post(
    "/supplier/purchase-orders/{purchase_order_id}/attachments",
    response_model=SupplierPurchaseOrderAttachmentResponse,
)
def create_supplier_purchase_order_attachment_route(
    purchase_order_id: int,
    payload: SupplierPurchaseOrderAttachmentCreateRequest,
    actor: AuthenticatedActor = Depends(supplier_purchase_order_reader_dependency),
    db: Session = Depends(get_db),
) -> SupplierPurchaseOrderAttachmentResponse:
    supplier_company_id = _resolve_supplier_purchase_order_scope(actor)
    try:
        attachment = create_supplier_purchase_order_attachment(
            db,
            purchase_order_id=purchase_order_id,
            supplier_company_id=supplier_company_id,
            operator_id=actor.user_id,
            biz_tag=payload.biz_tag,
            file_path=payload.file_path,
        )
    except OrderServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_supplier_purchase_order_attachment_response(
        attachment,
        message="供应商采购订单附件上传成功",
    )


def _resolve_sales_order_creator_scope(actor: AuthenticatedActor) -> str | None:
    if (
        actor.role_code == "customer"
        and actor.company_type == "customer_company"
        and actor.client_type == "miniprogram"
    ):
        if not actor.company_id:
            raise HTTPException(
                status_code=401, detail="未认证公司身份，禁止操作销售订单"
            )
        return actor.company_id

    if (
        actor.role_code in {"operations", "finance", "admin"}
        and actor.company_type == "operator_company"
        and actor.client_type == "admin_web"
    ):
        return None

    raise HTTPException(status_code=403, detail="当前身份无权操作销售订单")


def _resolve_customer_sales_order_scope(actor: AuthenticatedActor) -> str:
    if (
        actor.role_code == "customer"
        and actor.company_type == "customer_company"
        and actor.client_type == "miniprogram"
    ):
        if not actor.company_id:
            raise HTTPException(
                status_code=401, detail="未认证公司身份，禁止查询销售合同"
            )
        return actor.company_id
    raise HTTPException(status_code=403, detail="当前身份无权查询可选销售合同")


def _resolve_sales_order_reader_scope(actor: AuthenticatedActor) -> str | None:
    if (
        actor.role_code == "customer"
        and actor.company_type == "customer_company"
        and actor.client_type == "miniprogram"
    ):
        if not actor.company_id:
            raise HTTPException(
                status_code=401, detail="未认证公司身份，禁止查询销售订单"
            )
        return actor.company_id
    if (
        actor.role_code in {"operations", "finance", "admin"}
        and actor.company_type == "operator_company"
        and actor.client_type == "admin_web"
    ):
        return None
    raise HTTPException(status_code=403, detail="当前身份无权查询销售订单")


def _resolve_supplier_purchase_order_scope(actor: AuthenticatedActor) -> str:
    if (
        actor.role_code == "supplier"
        and actor.company_type == "supplier_company"
        and actor.client_type == "miniprogram"
    ):
        if not actor.company_id:
            raise HTTPException(
                status_code=401, detail="未认证公司身份，禁止查询采购订单"
            )
        return actor.company_id
    raise HTTPException(status_code=403, detail="当前身份无权查询采购订单")


def _to_sales_order_response(
    sales_order: SalesOrder,
    *,
    message: str,
    purchase_order_id: int | None = None,
    generated_task_count: int | None = None,
    sales_contract_no: str | None = None,
) -> SalesOrderResponse:
    resolved_purchase_order_id = purchase_order_id
    if resolved_purchase_order_id is None and sales_order.purchase_orders:
        resolved_purchase_order_id = sales_order.purchase_orders[0].id
    return SalesOrderResponse(
        id=sales_order.id,
        order_no=sales_order.order_no,
        sales_contract_id=sales_order.sales_contract_id,
        oil_product_id=sales_order.oil_product_id,
        qty_ordered=sales_order.qty_ordered,
        unit_price=sales_order.unit_price,
        status=sales_order.status,
        submit_comment=sales_order.submit_comment,
        ops_comment=sales_order.ops_comment,
        finance_comment=sales_order.finance_comment,
        submitted_at=sales_order.submitted_at,
        ops_approved_at=sales_order.ops_approved_at,
        finance_approved_at=sales_order.finance_approved_at,
        purchase_order_id=resolved_purchase_order_id,
        generated_task_count=generated_task_count
        if generated_task_count is not None
        else len(sales_order.derivative_tasks),
        message=message,
        sales_contract_no=sales_contract_no,
        created_at=sales_order.created_at,
    )


def _to_sales_order_list_item_response(
    sales_order: SalesOrder,
    *,
    sales_contract_no: str,
) -> SalesOrderListItemResponse:
    purchase_order_id = (
        sales_order.purchase_orders[0].id if sales_order.purchase_orders else None
    )
    return SalesOrderListItemResponse(
        id=sales_order.id,
        order_no=sales_order.order_no,
        sales_contract_id=sales_order.sales_contract_id,
        sales_contract_no=sales_contract_no,
        oil_product_id=sales_order.oil_product_id,
        qty_ordered=sales_order.qty_ordered,
        unit_price=sales_order.unit_price,
        status=sales_order.status,
        submit_comment=sales_order.submit_comment,
        ops_comment=sales_order.ops_comment,
        finance_comment=sales_order.finance_comment,
        purchase_order_id=purchase_order_id,
        submitted_at=sales_order.submitted_at,
        created_at=sales_order.created_at,
    )


def _to_available_sales_contract_response(
    contract: Contract,
) -> AvailableSalesContractResponse:
    return AvailableSalesContractResponse(
        id=contract.id,
        contract_no=contract.contract_no,
        customer_id=contract.customer_id or "",
        items=[
            AvailableSalesContractItemResponse(
                oil_product_id=item.oil_product_id,
                qty_signed=item.qty_signed,
                unit_price=item.unit_price,
            )
            for item in contract.items
        ],
    )


def _to_purchase_order_response(
    purchase_order: PurchaseOrder, *, message: str
) -> PurchaseOrderResponse:
    derivative_tasks = (
        purchase_order.sales_order.derivative_tasks
        if purchase_order.sales_order
        else []
    )
    return PurchaseOrderResponse(
        id=purchase_order.id,
        order_no=purchase_order.order_no,
        purchase_contract_id=purchase_order.purchase_contract_id,
        source_sales_order_id=purchase_order.source_sales_order_id,
        source_sales_order_no=purchase_order.sales_order.order_no
        if purchase_order.sales_order
        else None,
        supplier_id=purchase_order.supplier_id,
        oil_product_id=purchase_order.oil_product_id,
        qty_ordered=purchase_order.qty_ordered,
        payable_amount=purchase_order.payable_amount,
        status=purchase_order.status,
        zero_pay_exception_flag=purchase_order.zero_pay_exception_flag,
        downstream_tasks=[
            SalesOrderDerivativeTaskResponse(
                id=task.id,
                target_doc_type=task.target_doc_type,
                status=task.status,
                idempotency_key=task.idempotency_key,
            )
            for task in derivative_tasks
        ],
        message=message,
        created_at=purchase_order.created_at,
    )


def _to_purchase_order_list_item_response(
    purchase_order: PurchaseOrder,
    *,
    source_sales_order_no: str,
) -> PurchaseOrderListItemResponse:
    return PurchaseOrderListItemResponse(
        id=purchase_order.id,
        order_no=purchase_order.order_no,
        purchase_contract_id=purchase_order.purchase_contract_id,
        source_sales_order_id=purchase_order.source_sales_order_id,
        source_sales_order_no=source_sales_order_no,
        supplier_id=purchase_order.supplier_id,
        oil_product_id=purchase_order.oil_product_id,
        qty_ordered=purchase_order.qty_ordered,
        payable_amount=purchase_order.payable_amount,
        status=purchase_order.status,
        zero_pay_exception_flag=purchase_order.zero_pay_exception_flag,
        created_at=purchase_order.created_at,
    )


def _to_supplier_purchase_order_response(
    purchase_order: PurchaseOrder,
    *,
    message: str,
) -> SupplierPurchaseOrderResponse:
    return SupplierPurchaseOrderResponse(
        id=purchase_order.id,
        order_no=purchase_order.order_no,
        purchase_contract_id=purchase_order.purchase_contract_id,
        source_sales_order_id=purchase_order.source_sales_order_id,
        source_sales_order_no=purchase_order.sales_order.order_no
        if purchase_order.sales_order
        else None,
        supplier_id=purchase_order.supplier_id,
        oil_product_id=purchase_order.oil_product_id,
        qty_ordered=purchase_order.qty_ordered,
        payable_amount=purchase_order.payable_amount,
        status=purchase_order.status,
        zero_pay_exception_flag=purchase_order.zero_pay_exception_flag,
        supplier_confirm_comment=purchase_order.supplier_confirm_comment,
        supplier_confirmed_at=purchase_order.supplier_confirmed_at,
        message=message,
        created_at=purchase_order.created_at,
    )


def _to_supplier_purchase_order_attachment_response(
    attachment,
    *,
    message: str,
) -> SupplierPurchaseOrderAttachmentResponse:
    return SupplierPurchaseOrderAttachmentResponse(
        id=attachment.id,
        owner_doc_type=attachment.owner_doc_type,
        owner_doc_id=attachment.owner_doc_id,
        biz_tag=attachment.biz_tag,
        file_path=attachment.path,
        created_at=attachment.created_at,
        message=message,
    )


def _to_supplier_purchase_order_attachment_list_item(
    attachment,
) -> SupplierPurchaseOrderAttachmentListItemResponse:
    return SupplierPurchaseOrderAttachmentListItemResponse(
        id=attachment.id,
        owner_doc_type=attachment.owner_doc_type,
        owner_doc_id=attachment.owner_doc_id,
        biz_tag=attachment.biz_tag,
        file_path=attachment.path,
        created_at=attachment.created_at,
    )
