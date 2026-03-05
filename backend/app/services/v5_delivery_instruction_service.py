from __future__ import annotations

import re
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.master_data import OilProduct, Warehouse
from app.models.v5_domain import AgreementTemplate, AgreementTemplateVersion, Company, PurchaseOrderV5, SalesOrderV5
from app.services.file_storage_service import build_storage_key, save_binary_file

_PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")
_PDF_FONT_NAME = "STSong-Light"


class DeliveryInstructionGenerateError(RuntimeError):
    pass


def _safe_text(value: object) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"


def _snapshot_text(snapshot: dict[str, object] | None, key: str, fallback: object = "") -> str:
    if isinstance(snapshot, dict):
        text = str(snapshot.get(key) or "").strip()
        if text:
            return text
    return _safe_text(fallback)


def _build_context(
    *,
    purchase_order: PurchaseOrderV5,
    sales_order: SalesOrderV5,
    customer_company_name: str | None,
    supplier_company_name: str | None,
    warehouse_name: str | None,
    product_name: str | None,
) -> dict[str, str]:
    transport_snapshot = sales_order.transport_snapshot_json or {}
    purchase_contract_snapshot = purchase_order.purchase_contract_snapshot_json or {}
    buyer_company_name = _snapshot_text(
        purchase_contract_snapshot,
        "buyer_company_name",
        sales_order.operator_company_name_snapshot,
    )
    seller_company_name = _snapshot_text(purchase_contract_snapshot, "seller_company_name", supplier_company_name)
    return {
        "purchase_order_no": _safe_text(purchase_order.purchase_order_no),
        "sales_order_no": _safe_text(sales_order.sales_order_no),
        "order_date": _safe_text(sales_order.order_date),
        "contract_business_direction": "采购",
        "our_role_text": "买方",
        "counterparty_role_text": "卖方",
        "our_company_name": _snapshot_text(purchase_contract_snapshot, "our_company_name", buyer_company_name),
        "counterparty_company_name": _snapshot_text(
            purchase_contract_snapshot,
            "counterparty_company_name",
            seller_company_name,
        ),
        "buyer_company_name": buyer_company_name,
        "seller_company_name": seller_company_name,
        "customer_company_name": _safe_text(customer_company_name),
        "supplier_company_name": _safe_text(supplier_company_name),
        "warehouse_name": _safe_text(warehouse_name),
        "product_name": _safe_text(product_name),
        "qty_ton": _safe_text(purchase_order.qty_ton),
        "carrier_company": _safe_text(transport_snapshot.get("carrier_company")),
        "driver_name": _safe_text(transport_snapshot.get("driver_name")),
        "driver_phone": _safe_text(transport_snapshot.get("driver_phone")),
        "driver_id_no": _safe_text(transport_snapshot.get("driver_id_no")),
        "vehicle_no": _safe_text(transport_snapshot.get("vehicle_no")),
    }


def _render_lines(template_content_json: dict[str, object], context: dict[str, str]) -> list[str]:
    raw_content = str(template_content_json.get("content") or "").strip()
    if not raw_content:
        return [
            f"采购订单号：{context['purchase_order_no']}",
            f"销售订单号：{context['sales_order_no']}",
            f"我方主体：{context['our_company_name']}",
            f"交易对方：{context['counterparty_company_name']}",
            f"买方（运营方）：{context['buyer_company_name']}",
            f"卖方（供应商）：{context['seller_company_name']}",
            f"提货单位（客户）：{context['customer_company_name']}",
            f"仓库：{context['warehouse_name']}",
            f"油品：{context['product_name']}",
            f"数量(吨)：{context['qty_ton']}",
            f"运输单位：{context['carrier_company']}",
            f"司机姓名：{context['driver_name']}",
            f"联系电话：{context['driver_phone']}",
            f"身份证号：{context['driver_id_no']}",
            f"车牌号：{context['vehicle_no']}",
        ]

    def _replace(match: re.Match[str]) -> str:
        return context.get(match.group(1), "-")

    rendered = _PLACEHOLDER_PATTERN.sub(_replace, raw_content)
    lines = [line.strip() for line in rendered.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return [item for item in lines if item]


def _create_pdf_bytes(*, title: str, lines: list[str]) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise DeliveryInstructionGenerateError("未安装 reportlab，无法生成发货指令单 PDF") from exc

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


def generate_delivery_instruction_pdf(
    db: Session,
    *,
    purchase_order: PurchaseOrderV5,
    sales_order: SalesOrderV5,
    template: AgreementTemplate,
    template_version: AgreementTemplateVersion,
) -> str:
    customer_company_name = db.scalar(select(Company.company_name).where(Company.id == sales_order.customer_company_id))
    supplier_company_name = None
    if purchase_order.supplier_company_id is not None:
        supplier_company_name = db.scalar(select(Company.company_name).where(Company.id == purchase_order.supplier_company_id))
    warehouse_name = db.scalar(select(Warehouse.name).where(Warehouse.id == purchase_order.warehouse_id))
    product_name = db.scalar(select(OilProduct.name).where(OilProduct.id == purchase_order.product_id))

    context = _build_context(
        purchase_order=purchase_order,
        sales_order=sales_order,
        customer_company_name=customer_company_name,
        supplier_company_name=supplier_company_name,
        warehouse_name=warehouse_name,
        product_name=product_name,
    )
    lines = _render_lines(template_version.template_content_json, context)
    title = template_version.template_title or template.template_name or "发货指令单"
    try:
        content = _create_pdf_bytes(title=title, lines=lines)
    except DeliveryInstructionGenerateError:
        raise
    except Exception as exc:
        raise DeliveryInstructionGenerateError("发货指令单生成失败") from exc

    relative_key = build_storage_key(category="delivery-instruction", suffix=".pdf")
    file_out = save_binary_file(
        content=content,
        file_key=relative_key,
        content_type="application/pdf",
        original_filename=f"{purchase_order.purchase_order_no}.pdf",
    )
    return file_out.file_key
