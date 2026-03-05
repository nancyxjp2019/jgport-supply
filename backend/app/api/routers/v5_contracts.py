from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.v5_domain import ContractStatus
from app.schemas.v5_contract import (
    ContractPdfOut,
    ContractSubmitEffectiveRequest,
    ContractVoidRequest,
    PurchaseContractCreateRequest,
    PurchaseContractDetailOut,
    PurchaseContractListItemOut,
    PurchaseContractUpdateRequest,
    SalesContractCreateRequest,
    SalesContractDetailOut,
    SalesContractListItemOut,
    SalesContractUpdateRequest,
)
from app.services.business_log_service import write_business_log
from app.services.v5_contract_service import (
    create_purchase_contract,
    create_sales_contract,
    get_purchase_contract,
    get_sales_contract,
    list_purchase_contracts,
    list_sales_contracts,
    serialize_purchase_contract_detail,
    serialize_purchase_contract_list,
    serialize_sales_contract_detail,
    serialize_sales_contract_list,
    submit_effective_purchase_contract,
    submit_effective_sales_contract,
    update_purchase_contract,
    update_sales_contract,
    void_purchase_contract,
    void_sales_contract,
    generate_purchase_contract_pdf_file,
    generate_sales_contract_pdf_file,
)

router = APIRouter(tags=["v5-contracts"])


@router.get("/sales-contracts", response_model=list[SalesContractListItemOut])
def list_v5_sales_contracts(
    request: Request,
    status_value: ContractStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[SalesContractListItemOut]:
    rows = list_sales_contracts(
        db=db,
        current_user=current_user,
        status_value=status_value,
        page=page,
        page_size=page_size,
    )
    result = serialize_sales_contract_list(db=db, rows=rows)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_CONTRACT_LIST",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_CONTRACT",
        detail_json={"count": len(result)},
        auto_commit=True,
    )
    return result


@router.post("/sales-contracts", response_model=SalesContractDetailOut, status_code=status.HTTP_201_CREATED)
def create_v5_sales_contract(
    payload: SalesContractCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SalesContractDetailOut:
    row = create_sales_contract(db=db, payload=payload, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_CONTRACT_CREATE",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_CONTRACT",
        entity_id=str(row.id),
        detail_json={"contract_no": row.contract_no},
    )
    db.commit()
    db.refresh(row)
    return serialize_sales_contract_detail(db=db, row=row)


@router.get("/sales-contracts/{contract_id}", response_model=SalesContractDetailOut)
def get_v5_sales_contract(
    contract_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SalesContractDetailOut:
    row = get_sales_contract(db=db, contract_id=contract_id, current_user=current_user)
    result = serialize_sales_contract_detail(db=db, row=row)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_CONTRACT_DETAIL",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_CONTRACT",
        entity_id=str(row.id),
        auto_commit=True,
    )
    return result


@router.patch("/sales-contracts/{contract_id}", response_model=SalesContractDetailOut)
def update_v5_sales_contract(
    contract_id: int,
    payload: SalesContractUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SalesContractDetailOut:
    row = get_sales_contract(db=db, contract_id=contract_id)
    before_status = row.status.value
    row = update_sales_contract(db=db, contract=row, payload=payload, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_CONTRACT_UPDATE",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_CONTRACT",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
    )
    db.commit()
    db.refresh(row)
    return serialize_sales_contract_detail(db=db, row=row)


@router.post("/sales-contracts/{contract_id}/submit-effective", response_model=SalesContractDetailOut)
def submit_effective_v5_sales_contract(
    contract_id: int,
    payload: ContractSubmitEffectiveRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SalesContractDetailOut:
    row = get_sales_contract(db=db, contract_id=contract_id)
    before_status = row.status.value
    row = submit_effective_sales_contract(
        db=db,
        contract=row,
        signed_contract_file_key=payload.signed_contract_file_key,
        deposit_receipt_file_key=payload.deposit_receipt_file_key,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_CONTRACT_SUBMIT_EFFECTIVE",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_CONTRACT",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
    )
    db.commit()
    db.refresh(row)
    return serialize_sales_contract_detail(db=db, row=row)


@router.post("/sales-contracts/{contract_id}/generate-pdf", response_model=ContractPdfOut)
def generate_pdf_v5_sales_contract(
    contract_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ContractPdfOut:
    row = get_sales_contract(db=db, contract_id=contract_id)
    file_key = generate_sales_contract_pdf_file(db=db, contract=row, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_CONTRACT_GENERATE_PDF",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_CONTRACT",
        entity_id=str(row.id),
        detail_json={"file_key": file_key},
    )
    db.commit()
    return ContractPdfOut(file_key=file_key, file_url=serialize_sales_contract_detail(db=db, row=row).generated_pdf_file_url or "")


@router.post("/sales-contracts/{contract_id}/void", response_model=SalesContractDetailOut)
def void_v5_sales_contract(
    contract_id: int,
    payload: ContractVoidRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SalesContractDetailOut:
    row = get_sales_contract(db=db, contract_id=contract_id)
    before_status = row.status.value
    row = void_sales_contract(db=db, contract=row, reason=payload.reason, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_SALES_CONTRACT_VOID",
        result="SUCCESS",
        user=current_user,
        entity_type="SALES_CONTRACT",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(row)
    return serialize_sales_contract_detail(db=db, row=row)


@router.get("/purchase-contracts", response_model=list[PurchaseContractListItemOut])
def list_v5_purchase_contracts(
    request: Request,
    status_value: ContractStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.SUPPLIER, UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[PurchaseContractListItemOut]:
    rows = list_purchase_contracts(
        db=db,
        current_user=current_user,
        status_value=status_value,
        page=page,
        page_size=page_size,
    )
    result = serialize_purchase_contract_list(db=db, rows=rows)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_CONTRACT_LIST",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_CONTRACT",
        detail_json={"count": len(result)},
        auto_commit=True,
    )
    return result


@router.post("/purchase-contracts", response_model=PurchaseContractDetailOut, status_code=status.HTTP_201_CREATED)
def create_v5_purchase_contract(
    payload: PurchaseContractCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseContractDetailOut:
    row = create_purchase_contract(db=db, payload=payload, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_CONTRACT_CREATE",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_CONTRACT",
        entity_id=str(row.id),
        detail_json={"contract_no": row.contract_no},
    )
    db.commit()
    db.refresh(row)
    return serialize_purchase_contract_detail(db=db, row=row)


@router.get("/purchase-contracts/{contract_id}", response_model=PurchaseContractDetailOut)
def get_v5_purchase_contract(
    contract_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.SUPPLIER, UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseContractDetailOut:
    row = get_purchase_contract(db=db, contract_id=contract_id, current_user=current_user)
    result = serialize_purchase_contract_detail(db=db, row=row)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_CONTRACT_DETAIL",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_CONTRACT",
        entity_id=str(row.id),
        auto_commit=True,
    )
    return result


@router.patch("/purchase-contracts/{contract_id}", response_model=PurchaseContractDetailOut)
def update_v5_purchase_contract(
    contract_id: int,
    payload: PurchaseContractUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseContractDetailOut:
    row = get_purchase_contract(db=db, contract_id=contract_id)
    before_status = row.status.value
    row = update_purchase_contract(db=db, contract=row, payload=payload, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_CONTRACT_UPDATE",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_CONTRACT",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
    )
    db.commit()
    db.refresh(row)
    return serialize_purchase_contract_detail(db=db, row=row)


@router.post("/purchase-contracts/{contract_id}/submit-effective", response_model=PurchaseContractDetailOut)
def submit_effective_v5_purchase_contract(
    contract_id: int,
    payload: ContractSubmitEffectiveRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseContractDetailOut:
    row = get_purchase_contract(db=db, contract_id=contract_id)
    before_status = row.status.value
    row, stock_ins = submit_effective_purchase_contract(
        db=db,
        contract=row,
        signed_contract_file_key=payload.signed_contract_file_key,
        deposit_receipt_file_key=payload.deposit_receipt_file_key,
        current_user=current_user,
    )
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_CONTRACT_SUBMIT_EFFECTIVE",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_CONTRACT",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
        detail_json={"purchase_stock_in_ids": [item.id for item in stock_ins]},
    )
    for stock_in in stock_ins:
        write_business_log(
            db=db,
            request=request,
            action="V5_PURCHASE_STOCK_IN_CREATE",
            result="SUCCESS",
            user=current_user,
            entity_type="PURCHASE_STOCK_IN",
            entity_id=str(stock_in.id),
            after_status=stock_in.status.value,
            detail_json={"purchase_contract_id": row.id},
        )
    db.commit()
    db.refresh(row)
    return serialize_purchase_contract_detail(db=db, row=row)


@router.post("/purchase-contracts/{contract_id}/generate-pdf", response_model=ContractPdfOut)
def generate_pdf_v5_purchase_contract(
    contract_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ContractPdfOut:
    row = get_purchase_contract(db=db, contract_id=contract_id)
    file_key = generate_purchase_contract_pdf_file(db=db, contract=row, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_CONTRACT_GENERATE_PDF",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_CONTRACT",
        entity_id=str(row.id),
        detail_json={"file_key": file_key},
    )
    db.commit()
    return ContractPdfOut(file_key=file_key, file_url=serialize_purchase_contract_detail(db=db, row=row).generated_pdf_file_url or "")


@router.post("/purchase-contracts/{contract_id}/void", response_model=PurchaseContractDetailOut)
def void_v5_purchase_contract(
    contract_id: int,
    payload: ContractVoidRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.FINANCE, UserRole.OPERATOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> PurchaseContractDetailOut:
    row = get_purchase_contract(db=db, contract_id=contract_id)
    before_status = row.status.value
    row = void_purchase_contract(db=db, contract=row, reason=payload.reason, current_user=current_user)
    write_business_log(
        db=db,
        request=request,
        action="V5_PURCHASE_CONTRACT_VOID",
        result="SUCCESS",
        user=current_user,
        entity_type="PURCHASE_CONTRACT",
        entity_id=str(row.id),
        before_status=before_status,
        after_status=row.status.value,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(row)
    return serialize_purchase_contract_detail(db=db, row=row)
