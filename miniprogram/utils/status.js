const CONTRACT_STATUS_TEXT = {
  DRAFT: '草稿',
  PENDING_EFFECTIVE: '待生效',
  EFFECTIVE: '已生效',
  PARTIALLY_EXECUTED: '部分执行',
  COMPLETED: '已完成',
  VOIDED: '已作废',
};

const SALES_ORDER_STATUS_TEXT = {
  SUBMITTED: '待运营审核',
  OPERATOR_APPROVED: '待财务审核',
  CUSTOMER_PAYMENT_CONFIRMED: '采购执行中',
  READY_FOR_OUTBOUND: '待仓库出库',
  COMPLETED: '已完成',
  REJECTED: '已驳回',
  ABNORMAL_CLOSED: '异常关闭',
};

const PURCHASE_ORDER_STATUS_TEXT = {
  PENDING_SUBMIT: '待提交',
  SUPPLIER_PAYMENT_PENDING: '待财务上传付款凭证',
  SUPPLIER_REVIEW_PENDING: '待供应商审核',
  WAREHOUSE_PENDING: '待仓库出库',
  COMPLETED: '已完成',
  ABNORMAL_CLOSED: '异常关闭',
};

const PROGRESS_STATUS_TEXT = {
  PENDING: '待处理',
  CURRENT: '当前进行中',
  COMPLETED: '已完成',
  BLOCKED: '未开始',
  ABNORMAL: '异常关闭',
};

const REPORT_EXPORT_STATUS_TEXT = {
  GENERATED: '已生成',
  FAILED: '生成失败',
};

const GENERIC_STATUS_TEXT = {
  ...CONTRACT_STATUS_TEXT,
  ...SALES_ORDER_STATUS_TEXT,
  ...PURCHASE_ORDER_STATUS_TEXT,
  ...PROGRESS_STATUS_TEXT,
  ...REPORT_EXPORT_STATUS_TEXT,
};

function textByMap(map, value) {
  return map[value] || value || '-';
}

function toContractStatusText(status) {
  return textByMap(CONTRACT_STATUS_TEXT, status);
}

function toSalesOrderStatusText(status) {
  return textByMap(SALES_ORDER_STATUS_TEXT, status);
}

function toPurchaseOrderStatusText(status) {
  return textByMap(PURCHASE_ORDER_STATUS_TEXT, status);
}

function toProgressStatusText(status) {
  return textByMap(PROGRESS_STATUS_TEXT, status);
}

function toReportExportStatusText(status) {
  return textByMap(REPORT_EXPORT_STATUS_TEXT, status);
}

function toGenericStatusText(status) {
  return textByMap(GENERIC_STATUS_TEXT, status);
}

module.exports = {
  CONTRACT_STATUS_TEXT,
  SALES_ORDER_STATUS_TEXT,
  PURCHASE_ORDER_STATUS_TEXT,
  PROGRESS_STATUS_TEXT,
  REPORT_EXPORT_STATUS_TEXT,
  toContractStatusText,
  toSalesOrderStatusText,
  toPurchaseOrderStatusText,
  toProgressStatusText,
  toReportExportStatusText,
  toGenericStatusText,
};
