const DEMO_WAREHOUSE_ID = 'DEMO-WH-001';

function normalizeText(value) {
  return String(value || '').trim();
}

function validatePositiveNumberText(value, fieldLabel) {
  const normalized = normalizeText(value);
  if (!normalized) {
    return `${fieldLabel}不能为空`;
  }
  const numericValue = Number(normalized);
  if (!Number.isFinite(numericValue) || numericValue <= 0) {
    return `${fieldLabel}必须大于0`;
  }
  return '';
}

function buildWarehouseConfirmPayload(form) {
  const payload = {
    contract_id: normalizeText(form.contractId),
    sales_order_id: normalizeText(form.salesOrderId),
    source_ticket_no: normalizeText(form.sourceTicketNo),
    actual_qty: normalizeText(form.actualQty),
    warehouse_id: normalizeText(form.warehouseId),
  };
  const errors = {
    contractId: validatePositiveNumberText(payload.contract_id, '销售合同ID'),
    salesOrderId: validatePositiveNumberText(payload.sales_order_id, '销售订单ID'),
    sourceTicketNo: payload.source_ticket_no ? '' : '仓库回执号不能为空',
    actualQty: validatePositiveNumberText(payload.actual_qty, '实际出库数量'),
    warehouseId: payload.warehouse_id ? '' : '仓库ID不能为空',
  };
  return {
    isValid: Object.values(errors).every((item) => !item),
    payload,
    errors,
  };
}

function buildManualOutboundPayload(form) {
  const payload = {
    contract_id: normalizeText(form.contractId),
    sales_order_id: normalizeText(form.salesOrderId),
    oil_product_id: normalizeText(form.oilProductId),
    manual_ref_no: normalizeText(form.manualRefNo),
    actual_qty: normalizeText(form.actualQty),
    reason: normalizeText(form.reason),
    warehouse_id: normalizeText(form.warehouseId),
  };
  const errors = {
    contractId: validatePositiveNumberText(payload.contract_id, '销售合同ID'),
    salesOrderId: validatePositiveNumberText(payload.sales_order_id, '销售订单ID'),
    oilProductId: payload.oil_product_id ? '' : '油品ID不能为空',
    manualRefNo: payload.manual_ref_no ? '' : '手工回执号不能为空',
    actualQty: validatePositiveNumberText(payload.actual_qty, '实际出库数量'),
    reason: payload.reason ? '' : '手工补录原因不能为空',
    warehouseId: payload.warehouse_id ? '' : '仓库ID不能为空',
  };
  return {
    isValid: Object.values(errors).every((item) => !item),
    payload,
    errors,
  };
}

function buildDemoExecResponse(mode, payload) {
  const timestamp = Date.now();
  return {
    id: timestamp,
    doc_no: `OUT-DEMO-${String(timestamp).slice(-6)}`,
    contract_id: Number(payload.contract_id),
    sales_order_id: Number(payload.sales_order_id),
    oil_product_id: mode === 'system' ? 'DEMO-OIL-92' : payload.oil_product_id,
    warehouse_id: payload.warehouse_id || DEMO_WAREHOUSE_ID,
    source_type: mode === 'system' ? 'SYSTEM' : 'MANUAL',
    source_ticket_no: mode === 'system' ? payload.source_ticket_no : null,
    manual_ref_no: mode === 'manual' ? payload.manual_ref_no : null,
    actual_qty: payload.actual_qty,
    status: '已过账',
    submitted_at: new Date(timestamp).toISOString(),
    created_at: new Date(timestamp).toISOString(),
    message: mode === 'system' ? '演示模式：仓库回执已模拟生效' : '演示模式：手工补录已模拟生效',
  };
}

function buildExecSummary(responseData, mode) {
  const docNo = normalizeText(responseData.doc_no);
  const actualQty = normalizeText(responseData.actual_qty);
  const sourceNo = mode === 'system' ? normalizeText(responseData.source_ticket_no) : normalizeText(responseData.manual_ref_no);
  return [
    { label: '出库单号', value: docNo || '-' },
    { label: mode === 'system' ? '仓库回执号' : '手工回执号', value: sourceNo || '-' },
    { label: '实际出库数量', value: actualQty || '-' },
    { label: '处理结果', value: normalizeText(responseData.status) || '-' },
  ];
}

module.exports = {
  buildDemoExecResponse,
  buildExecSummary,
  buildManualOutboundPayload,
  buildWarehouseConfirmPayload,
  resolveDefaultWarehouseId() {
    return DEMO_WAREHOUSE_ID;
  },
};
