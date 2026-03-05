from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.v5_domain import SalesOrderV5Status

_CHINA_MOBILE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
_VEHICLE_PLATE_PATTERN = re.compile(
    r"^[\u4e00-\u9fa5][A-Z](?:[A-HJ-NP-Z0-9]{5}|[DF][A-HJ-NP-Z0-9]{5}|[A-HJ-NP-Z0-9]{5}[DF])$"
)


def _contains_whitespace(value: str) -> bool:
    return any(char.isspace() for char in value)


def _validate_china_id_no(id_no: str) -> bool:
    normalized = id_no.upper()
    if not re.fullmatch(r"\d{17}[0-9X]", normalized):
        return False
    try:
        datetime.strptime(normalized[6:14], "%Y%m%d")
    except ValueError:
        return False
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_map = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]
    total = sum(int(normalized[index]) * weights[index] for index in range(17))
    return normalized[-1] == check_map[total % 11]


class TransportSnapshotIn(BaseModel):
    carrier_company: str = Field(min_length=1, max_length=128)
    driver_name: str = Field(min_length=1, max_length=16)
    driver_phone: str = Field(min_length=1, max_length=11)
    driver_id_no: str = Field(min_length=1, max_length=18)
    vehicle_no: str = Field(min_length=1, max_length=8)
    tank_type: str | None = Field(default=None, max_length=32)
    with_pump: bool | None = None
    rated_load_ton: int | None = Field(default=None, gt=0)
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("carrier_company", "driver_name", "driver_phone", "driver_id_no", "vehicle_no", mode="before")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("remark", mode="before")
    @classmethod
    def normalize_remark(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("carrier_company")
    @classmethod
    def validate_carrier_company(cls, value: str) -> str:
        if _contains_whitespace(value):
            raise ValueError("运输单位不能包含空格")
        return value

    @field_validator("driver_name")
    @classmethod
    def validate_driver_name(cls, value: str) -> str:
        if _contains_whitespace(value):
            raise ValueError("司机姓名不能包含空格")
        if re.fullmatch(r"[\u4e00-\u9fff]{1,4}", value) is None:
            raise ValueError("司机姓名必须为1到4个汉字")
        return value

    @field_validator("driver_phone")
    @classmethod
    def validate_driver_phone(cls, value: str) -> str:
        if _contains_whitespace(value):
            raise ValueError("手机号不能包含空格")
        if _CHINA_MOBILE_PATTERN.fullmatch(value) is None:
            raise ValueError("手机号格式不正确")
        return value

    @field_validator("driver_id_no")
    @classmethod
    def validate_driver_id_no(cls, value: str) -> str:
        normalized = value.upper()
        if _contains_whitespace(normalized):
            raise ValueError("身份证不能包含空格")
        if not _validate_china_id_no(normalized):
            raise ValueError("身份证格式不正确")
        return normalized

    @field_validator("vehicle_no")
    @classmethod
    def validate_vehicle_no(cls, value: str) -> str:
        normalized = value.upper()
        if _contains_whitespace(normalized):
            raise ValueError("车牌号不能包含空格")
        if _VEHICLE_PLATE_PATTERN.fullmatch(normalized) is None:
            raise ValueError("车牌号格式不正确")
        return normalized

    @field_validator("tank_type", mode="before")
    @classmethod
    def normalize_tank_type(cls, value: str | None) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        return {
            "单仓": "单枪",
            "双仓": "双枪",
            "单枪": "单枪",
            "双枪": "双枪",
        }.get(text, text)

    @field_validator("tank_type")
    @classmethod
    def validate_tank_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in {"单枪", "双枪"}:
            raise ValueError("单双枪仅支持单枪或双枪")
        return value


class SalesOrderCreateRequest(BaseModel):
    order_date: date
    warehouse_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    sales_contract_id: int = Field(gt=0)
    qty_ton: float = Field(gt=0)
    transport_profile_id: int | None = Field(default=None, gt=0)
    transport_snapshot: TransportSnapshotIn
    transport_file_keys: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("transport_file_keys", mode="before")
    @classmethod
    def normalize_transport_file_keys(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("付款凭证附件必须为数组")
        result: list[str] = []
        for item in value:
            text = str(item or "").strip().strip("/")
            if not text:
                raise ValueError("付款凭证附件不能为空")
            result.append(text)
        return result

    @model_validator(mode="after")
    def validate_qty_precision(self) -> "SalesOrderCreateRequest":
        try:
            qty = Decimal(str(self.qty_ton))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("数量(吨)格式不正确") from exc
        if qty <= 0:
            raise ValueError("数量(吨)必须大于0")
        if qty.as_tuple().exponent < -4:
            raise ValueError("数量(吨)最多保留4位小数")
        if not self.transport_file_keys:
            raise ValueError("付款凭证至少上传1个文件")
        return self


class SalesOrderOperatorReviewRequest(BaseModel):
    action: str = Field(default="approve")

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized != "approve":
            raise ValueError("当前仅支持 approve")
        return normalized


class SalesOrderFinanceReviewRequest(BaseModel):
    action: str = Field(default="approve")
    received_amount: float = Field(gt=0)
    customer_payment_receipt_file_key: str = Field(min_length=1, max_length=255)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized != "approve":
            raise ValueError("当前仅支持 approve")
        return normalized

    @field_validator("customer_payment_receipt_file_key", mode="before")
    @classmethod
    def normalize_file_key(cls, value: str) -> str:
        return str(value or "").strip().strip("/")


class SalesOrderTerminateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("终止原因不能为空")
        return text


class SalesOrderListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sales_order_no: str
    order_date: date
    customer_company_id: int
    customer_company_name: str
    warehouse_id: int
    warehouse_name: str
    product_id: int
    product_name: str
    sales_contract_id: int
    sales_contract_no: str
    qty_ton: float
    unit_price_tax_included: float
    amount_tax_included: float
    amount_tax_excluded: float | None
    tax_amount: float | None
    status: SalesOrderV5Status
    reserved_qty_ton: float
    actual_outbound_qty_ton: float
    received_amount: float | None
    closed_reason: str | None
    closed_by: int | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SalesOrderDetailOut(SalesOrderListItemOut):
    buyer_company_name: str | None = None
    seller_company_name: str | None = None
    contract_signing_subject_name: str | None = None
    transport_profile_id: int | None
    transport_snapshot: dict[str, object]
    transport_file_keys: list[str]
    transport_file_names: list[str]
    transport_file_urls: list[str]
    customer_payment_receipt_file_key: str | None
    customer_payment_receipt_file_url: str | None
    customer_payment_receipt_file_name: str | None = None
    operator_company_id: int | None
    operator_company_name_snapshot: str | None
    operator_reviewed_by: int | None
    operator_reviewed_at: datetime | None
    finance_reviewed_by: int | None
    finance_reviewed_at: datetime | None
    purchase_order_id: int | None
