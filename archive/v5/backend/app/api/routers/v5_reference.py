from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.v5_reference import (
    AgreementTemplateSelectOptionOut,
    PurchaseContractSelectOptionOut,
    SalesContractSelectOptionOut,
    SalesOrderCreateMetaOut,
    TransportProfileHistoryItemOut,
)
from app.services.v5_reference_service import (
    build_sales_order_create_meta,
    delete_transport_history_item,
    list_purchase_contract_select_options,
    list_sales_contract_select_options,
    list_template_select_options,
    list_transport_history,
)

router = APIRouter(tags=["v5-reference"])


@router.get("/agreement-templates/select-options", response_model=list[AgreementTemplateSelectOptionOut])
def get_agreement_template_select_options(
    template_type: str | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.FINANCE)),
    db: Session = Depends(get_db),
) -> list[AgreementTemplateSelectOptionOut]:
    return list_template_select_options(db=db, raw_template_type=template_type)


@router.get("/transport-profiles/history", response_model=list[TransportProfileHistoryItemOut])
def get_transport_profile_history(
    current_user: User = Depends(require_roles(UserRole.CUSTOMER)),
    db: Session = Depends(get_db),
) -> list[TransportProfileHistoryItemOut]:
    return list_transport_history(db=db, current_user=current_user)


@router.delete("/transport-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transport_profile_history(
    profile_id: int,
    current_user: User = Depends(require_roles(UserRole.CUSTOMER)),
    db: Session = Depends(get_db),
) -> Response:
    delete_transport_history_item(db=db, profile_id=profile_id, current_user=current_user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sales-contracts/select-options", response_model=list[SalesContractSelectOptionOut])
def get_sales_contract_select_options(
    qty: float | None = Query(default=None, gt=0),
    current_user: User = Depends(require_roles(UserRole.CUSTOMER)),
    db: Session = Depends(get_db),
) -> list[SalesContractSelectOptionOut]:
    return list_sales_contract_select_options(db=db, current_user=current_user, qty=qty)


@router.get("/purchase-contracts/select-options", response_model=list[PurchaseContractSelectOptionOut])
def get_purchase_contract_select_options(
    product_id: int = Query(gt=0),
    warehouse_id: int = Query(gt=0),
    qty: float = Query(gt=0),
    _: User = Depends(require_roles(UserRole.FINANCE)),
    db: Session = Depends(get_db),
) -> list[PurchaseContractSelectOptionOut]:
    return list_purchase_contract_select_options(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        qty=qty,
    )


@router.get("/sales-orders/create-meta", response_model=SalesOrderCreateMetaOut)
def get_sales_order_create_meta(
    current_user: User = Depends(require_roles(UserRole.CUSTOMER)),
    db: Session = Depends(get_db),
) -> SalesOrderCreateMetaOut:
    return build_sales_order_create_meta(db=db, current_user=current_user)
