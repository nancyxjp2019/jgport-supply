function normalizeText(value) {
  return String(value || '').trim();
}

function getOrderStatusOptions() {
  return [
    { key: '', label: '全部' },
    { key: '草稿', label: '草稿' },
    { key: '待运营审批', label: '待运营审批' },
    { key: '待财务审批', label: '待财务审批' },
    { key: '驳回', label: '驳回' },
    { key: '已衍生采购订单', label: '已衍生采购订单' },
  ];
}

function adaptContractOptions(contracts) {
  return (contracts || []).map((contract) => ({
    id: Number(contract.id),
    contractNo: contract.contract_no,
    customerId: contract.customer_id,
    items: (contract.items || []).map((item) => ({
      oilProductId: item.oil_product_id,
      qtySigned: item.qty_signed,
      unitPrice: item.unit_price,
    })),
  }));
}

function getOrderStatusClass(status) {
  const normalized = normalizeText(status);
  if (normalized === '草稿') {
    return 'status-pill--draft';
  }
  if (normalized === '驳回') {
    return 'status-pill--rejected';
  }
  if (normalized === '待运营审批' || normalized === '待财务审批') {
    return 'status-pill--pending';
  }
  if (normalized === '已衍生采购订单' || normalized === '执行中') {
    return 'status-pill--progress';
  }
  if (normalized === '已完成') {
    return 'status-pill--done';
  }
  return 'status-pill--normal';
}

function canEditOrder(status) {
  return ['草稿', '驳回'].includes(normalizeText(status));
}

function buildOrderDraftPayload(form) {
  const payload = {
    sales_contract_id: normalizeText(form.salesContractId),
    oil_product_id: normalizeText(form.oilProductId),
    qty: normalizeText(form.qty),
    unit_price: normalizeText(form.unitPrice),
  };
  const errors = {
    salesContractId: payload.sales_contract_id ? '' : '请选择合同',
    oilProductId: payload.oil_product_id ? '' : '请选择油品',
    qty: validatePositiveNumberText(payload.qty, '下单数量'),
    unitPrice: validatePositiveNumberText(payload.unit_price, '合同单价'),
  };
  return {
    isValid: Object.values(errors).every((item) => !item),
    payload,
    errors,
  };
}

function validateSubmitComment(comment) {
  return normalizeText(comment) ? '' : '提交审批说明不能为空';
}

function buildOrderEditorState(order, contractOptions) {
  const contractIndex = (contractOptions || []).findIndex((item) => item.id === Number(order.sales_contract_id));
  const resolvedContract = contractIndex >= 0 ? contractOptions[contractIndex] : null;
  const oilIndex = resolvedContract
    ? resolvedContract.items.findIndex((item) => item.oilProductId === order.oil_product_id)
    : -1;
  return {
    editingOrderId: Number(order.id),
    selectedContractIndex: contractIndex >= 0 ? contractIndex : 0,
    selectedOilIndex: oilIndex >= 0 ? oilIndex : 0,
    form: {
      salesContractId: String(order.sales_contract_id),
      oilProductId: order.oil_product_id,
      qty: String(order.qty_ordered),
      unitPrice: String(order.unit_price),
      submitComment: order.submit_comment || '',
    },
  };
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

module.exports = {
  adaptContractOptions,
  buildOrderDraftPayload,
  buildOrderEditorState,
  canEditOrder,
  getOrderStatusClass,
  getOrderStatusOptions,
  validateSubmitComment,
};
