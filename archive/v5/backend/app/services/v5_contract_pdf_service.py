from __future__ import annotations

from decimal import Decimal
from io import BytesIO
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.master_data import OilProduct, Warehouse
from app.models.v5_domain import Company, PurchaseContract, PurchaseContractItem, SalesContract, SalesContractItem
from app.services.file_storage_service import build_storage_key, save_binary_file

_PDF_FONT_NAME = "STSong-Light"


class ContractPdfGenerateError(RuntimeError):
    pass


def _safe_text(value: object) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"


def _format_money_text(value: object) -> str:
    try:
        amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return _safe_text(value)
    return format(amount, ",.2f")


def _format_percent_text(value: object) -> str:
    try:
        rate = Decimal(str(value or 0)).quantize(Decimal("0.0000"))
    except Exception:
        return _safe_text(value)
    text = format((rate * Decimal("100")).quantize(Decimal("0.01")), "f").rstrip("0").rstrip(".")
    return f"{text}%"


def _create_pdf_bytes(*, title: str, lines: list[str]) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise ContractPdfGenerateError("未安装 reportlab，无法生成合同 PDF") from exc

    page_width, page_height = A4
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdfmetrics.registerFont(UnicodeCIDFont(_PDF_FONT_NAME))
    pdf.setTitle(title)

    y = page_height - 72
    pdf.setFont(_PDF_FONT_NAME, 20)
    pdf.drawCentredString(page_width / 2, y, title)
    pdf.setFont(_PDF_FONT_NAME, 12)
    y -= 36

    for line in lines:
        if y < 72:
            pdf.showPage()
            pdf.setFont(_PDF_FONT_NAME, 12)
            y = page_height - 72
        pdf.drawString(72, y, line)
        y -= 22

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _render_template_lines(template_snapshot: dict[str, object] | None, variable_snapshot: dict[str, object] | None) -> list[str]:
    template_snapshot = template_snapshot or {}
    variable_snapshot = variable_snapshot or {}
    template_content_json = template_snapshot.get("template_content_json")
    if not isinstance(template_content_json, dict):
        return []
    content_text = str(template_content_json.get("content") or "").strip()
    if not content_text:
        return []
    rendered_lines: list[str] = []
    for raw_line in content_text.splitlines():
        line = re.sub(
            r"\{\{(.*?)\}\}",
            lambda matched: _safe_text(variable_snapshot.get(str(matched.group(1) or "").strip(), "")),
            raw_line,
        )
        rendered_lines.append(line or " ")
    return rendered_lines


def _snapshot_text(variable_snapshot: dict[str, object] | None, key: str, fallback: object = "") -> str:
    if isinstance(variable_snapshot, dict):
        text = str(variable_snapshot.get(key) or "").strip()
        if text:
            return text
    return _safe_text(fallback)


def _build_item_lines(item_rows, product_name_map: dict[int, str]) -> list[str]:
    if not item_rows:
        return ["合同条目：暂无条目"]
    lines = ["合同条目："]
    total_qty = 0.0
    total_amount_tax_included = 0.0
    for index, item in enumerate(item_rows, start=1):
        total_qty += float(item.qty_ton)
        total_amount_tax_included += float(item.amount_tax_included)
        lines.append(
            "；".join(
                [
                    f"{index}.{_safe_text(product_name_map.get(item.product_id))}",
                    f"数量(吨)：{_safe_text(item.qty_ton)}",
                    f"税率：{_format_percent_text(item.tax_rate)}",
                    f"含税单价：{_format_money_text(item.unit_price_tax_included)}",
                    f"含税金额：{_format_money_text(item.amount_tax_included)}",
                ]
            )
        )
    lines.append(f"合计数量(吨)：{total_qty:.4f}")
    lines.append(f"合计含税金额：{_format_money_text(total_amount_tax_included)}")
    return lines


def generate_sales_contract_pdf(db: Session, *, contract: SalesContract) -> str:
    variable_snapshot = contract.variable_snapshot_json or {}
    customer_company_name = db.scalar(select(Company.company_name).where(Company.id == contract.customer_company_id))
    our_company_name = _snapshot_text(
        variable_snapshot,
        "our_company_name",
        _snapshot_text(variable_snapshot, "seller_company_name"),
    )
    counterparty_company_name = _snapshot_text(variable_snapshot, "counterparty_company_name", customer_company_name)
    buyer_company_name = _snapshot_text(variable_snapshot, "buyer_company_name", customer_company_name)
    seller_company_name = _snapshot_text(variable_snapshot, "seller_company_name", our_company_name)
    our_role_text = _snapshot_text(variable_snapshot, "our_role_text", "卖方")
    counterparty_role_text = _snapshot_text(variable_snapshot, "counterparty_role_text", "买方")
    item_rows = db.scalars(
        select(SalesContractItem).where(SalesContractItem.sales_contract_id == contract.id).order_by(SalesContractItem.id.asc())
    ).all()
    product_name_map = dict(
        db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_({item.product_id for item in item_rows}))).all()
    ) if item_rows else {}
    lines = _render_template_lines(contract.template_snapshot_json, variable_snapshot)
    if not lines:
        lines = [
            f"合同编号：{_safe_text(contract.contract_no)}",
            f"我方主体：{our_company_name}",
            f"交易对方：{counterparty_company_name}",
            f"买方：{buyer_company_name}",
            f"卖方：{seller_company_name}",
            f"合同日期：{_safe_text(contract.contract_date)}",
        ]
    lines.extend(
        [
            f"合同状态：{_safe_text(contract.status.value)}",
            f"我方主体：{our_company_name}",
            f"交易对方：{counterparty_company_name}",
            f"我方角色：{our_role_text}",
            f"对方角色：{counterparty_role_text}",
            f"合同总量(吨)：{_safe_text(contract.effective_contract_qty)}",
            f"保证金比例：{_format_percent_text(contract.deposit_rate)}",
            f"保证金金额：{_format_money_text(contract.deposit_amount)}",
        ]
    )
    lines.extend(_build_item_lines(item_rows, product_name_map))
    title = str((contract.template_snapshot_json or {}).get("template_title") or "销售合同")
    file_out = save_binary_file(
        content=_create_pdf_bytes(title=title, lines=lines),
        file_key=build_storage_key(category="sales-contract", suffix=".pdf"),
        content_type="application/pdf",
        original_filename=f"{contract.contract_no}.pdf",
    )
    return file_out.file_key


def generate_purchase_contract_pdf(db: Session, *, contract: PurchaseContract) -> str:
    variable_snapshot = contract.variable_snapshot_json or {}
    supplier_company_name = db.scalar(select(Company.company_name).where(Company.id == contract.supplier_company_id))
    our_company_name = _snapshot_text(
        variable_snapshot,
        "our_company_name",
        _snapshot_text(variable_snapshot, "buyer_company_name"),
    )
    counterparty_company_name = _snapshot_text(variable_snapshot, "counterparty_company_name", supplier_company_name)
    buyer_company_name = _snapshot_text(variable_snapshot, "buyer_company_name", our_company_name)
    seller_company_name = _snapshot_text(variable_snapshot, "seller_company_name", supplier_company_name)
    our_role_text = _snapshot_text(variable_snapshot, "our_role_text", "买方")
    counterparty_role_text = _snapshot_text(variable_snapshot, "counterparty_role_text", "卖方")
    warehouse_id = int((contract.template_snapshot_json or {}).get("warehouse_id") or 0)
    warehouse_name = db.scalar(select(Warehouse.name).where(Warehouse.id == warehouse_id)) if warehouse_id > 0 else None
    item_rows = db.scalars(
        select(PurchaseContractItem).where(PurchaseContractItem.purchase_contract_id == contract.id).order_by(PurchaseContractItem.id.asc())
    ).all()
    product_name_map = dict(
        db.execute(select(OilProduct.id, OilProduct.name).where(OilProduct.id.in_({item.product_id for item in item_rows}))).all()
    ) if item_rows else {}
    lines = _render_template_lines(contract.template_snapshot_json, variable_snapshot)
    if not lines:
        lines = [
            f"合同编号：{_safe_text(contract.contract_no)}",
            f"我方主体：{our_company_name}",
            f"交易对方：{counterparty_company_name}",
            f"买方：{buyer_company_name}",
            f"卖方：{seller_company_name}",
            f"仓库：{_safe_text(warehouse_name)}",
            f"合同日期：{_safe_text(contract.contract_date)}",
        ]
    lines.extend(
        [
            f"合同状态：{_safe_text(contract.status.value)}",
            f"我方主体：{our_company_name}",
            f"交易对方：{counterparty_company_name}",
            f"我方角色：{our_role_text}",
            f"对方角色：{counterparty_role_text}",
            f"仓库：{_safe_text(warehouse_name)}",
            f"合同总量(吨)：{_safe_text(contract.effective_contract_qty)}",
            f"保证金比例：{_format_percent_text(contract.deposit_rate)}",
            f"保证金金额：{_format_money_text(contract.deposit_amount)}",
        ]
    )
    lines.extend(_build_item_lines(item_rows, product_name_map))
    title = str((contract.template_snapshot_json or {}).get("template_title") or "采购合同")
    file_out = save_binary_file(
        content=_create_pdf_bytes(title=title, lines=lines),
        file_key=build_storage_key(category="purchase-contract", suffix=".pdf"),
        content_type="application/pdf",
        original_filename=f"{contract.contract_no}.pdf",
    )
    return file_out.file_key
