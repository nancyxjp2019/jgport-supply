const { request } = require('./request');
const { buildQueryString } = require('./format');

function getSalesOrderCreateMeta() {
  return request({ url: '/sales-orders/create-meta' });
}

function getTransportHistory() {
  return request({ url: '/transport-profiles/history' });
}

function deleteTransportProfile(profileId) {
  return request({
    url: `/transport-profiles/${profileId}`,
    method: 'DELETE',
  });
}

function createSalesOrder(payload) {
  return request({
    url: '/sales-orders',
    method: 'POST',
    data: payload,
  });
}

function listSalesOrders(params = {}) {
  return request({
    url: `/sales-orders${buildQueryString(params)}`,
  });
}

function getSalesOrderDetail(orderId) {
  return request({ url: `/sales-orders/${orderId}` });
}

function getSalesOrderProgress(orderId) {
  return request({ url: `/sales-orders/${orderId}/progress` });
}

function getSalesOrderLogs(orderId) {
  return request({ url: `/sales-orders/${orderId}/logs` });
}

function operatorApproveSalesOrder(orderId) {
  return request({
    url: `/sales-orders/${orderId}/operator-review`,
    method: 'PATCH',
    data: { action: 'approve' },
  });
}

function financeApproveSalesOrder(orderId, payload) {
  return request({
    url: `/sales-orders/${orderId}/finance-review`,
    method: 'PATCH',
    data: payload,
  });
}

function rejectSalesOrder(orderId, reason) {
  return request({
    url: `/sales-orders/${orderId}/reject`,
    method: 'PATCH',
    data: { reason },
  });
}

function abnormalCloseSalesOrder(orderId, reason) {
  return request({
    url: `/sales-orders/${orderId}/abnormal-close`,
    method: 'PATCH',
    data: { reason },
  });
}

function listPurchaseOrders(params = {}) {
  return request({
    url: `/purchase-orders${buildQueryString(params)}`,
  });
}

function getPurchaseOrderDetail(orderId) {
  return request({ url: `/purchase-orders/${orderId}` });
}

function getPurchaseOrderLogs(orderId) {
  return request({ url: `/purchase-orders/${orderId}/logs` });
}

function getPurchaseContractOptions(params) {
  return request({
    url: `/purchase-contracts/select-options${buildQueryString(params)}`,
  });
}

function getDeliveryTemplates() {
  return request({
    url: '/agreement-templates/select-options?template_type=DELIVERY_INSTRUCTION',
  });
}

function submitPurchaseOrder(orderId, payload) {
  return request({
    url: `/purchase-orders/${orderId}/submit`,
    method: 'PATCH',
    data: payload,
  });
}


function supplierReviewPurchaseOrder(orderId, supplierDeliveryDocFileKey) {
  return request({
    url: `/purchase-orders/${orderId}/supplier-review`,
    method: 'PATCH',
    data: { supplier_delivery_doc_file_key: supplierDeliveryDocFileKey },
  });
}

function warehouseOutboundPurchaseOrder(orderId, payload) {
  return request({
    url: `/purchase-orders/${orderId}/warehouse-outbound`,
    method: 'PATCH',
    data: payload,
  });
}

function abnormalClosePurchaseOrder(orderId, reason) {
  return request({
    url: `/purchase-orders/${orderId}/abnormal-close`,
    method: 'PATCH',
    data: { reason },
  });
}

function listSalesContracts(params = {}) {
  return request({
    url: `/sales-contracts${buildQueryString(params)}`,
  });
}

function listPurchaseContracts(params = {}) {
  return request({
    url: `/purchase-contracts${buildQueryString(params)}`,
  });
}

function getInventorySummary(params = {}) {
  return request({
    url: `/inventory/summary${buildQueryString(params)}`,
  });
}

const REPORT_ROUTE_MAP = {
  SALES_ORDERS: '/reports/sales-orders',
  PURCHASE_ORDERS: '/reports/purchase-orders',
  SALES_CONTRACTS: '/reports/sales-contracts',
  PURCHASE_CONTRACTS: '/reports/purchase-contracts',
  INVENTORY_MOVEMENTS: '/reports/inventory-movements',
  WAREHOUSE_LEDGER: '/reports/warehouse-ledger',
};

function listReports(reportType, params = {}) {
  return request({
    url: `${REPORT_ROUTE_MAP[reportType]}${buildQueryString(params)}`,
  });
}

function generateReport(reportType, payload) {
  return request({
    url: `${REPORT_ROUTE_MAP[reportType]}/generate`,
    method: 'POST',
    data: payload,
  });
}

module.exports = {
  abnormalClosePurchaseOrder,
  abnormalCloseSalesOrder,
  createSalesOrder,
  deleteTransportProfile,
  financeApproveSalesOrder,
  generateReport,
  getDeliveryTemplates,
  getInventorySummary,
  getPurchaseContractOptions,
  getPurchaseOrderDetail,
  getPurchaseOrderLogs,
  getSalesOrderCreateMeta,
  getSalesOrderDetail,
  getSalesOrderLogs,
  getSalesOrderProgress,
  getTransportHistory,
  listPurchaseContracts,
  listPurchaseOrders,
  listReports,
  listSalesContracts,
  listSalesOrders,
  operatorApproveSalesOrder,
  rejectSalesOrder,
  submitPurchaseOrder,
  supplierReviewPurchaseOrder,
  warehouseOutboundPurchaseOrder,
};
