const { getRuntimeMode } = require('../config/env');
const {
  createDemoSalesOrder,
  listDemoAvailableSalesContracts,
  listDemoSalesOrders,
  submitDemoSalesOrder,
  updateDemoSalesOrder,
} = require('../mocks/order');
const { getDemoLightReportOverview } = require('../mocks/report');
const { request } = require('./request');
const { buildDemoExecResponse } = require('./warehouse-exec');

function sleep(timeout) {
  return new Promise((resolve) => setTimeout(resolve, timeout));
}

async function getLightReportOverview() {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    return {
      data: getDemoLightReportOverview(),
      statusCode: 200,
    };
  }

  return request({
    url: '/reports/light/overview',
    method: 'GET',
  });
}

async function getAvailableSalesContracts() {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    const items = listDemoAvailableSalesContracts();
    return {
      data: {
        items,
        total: items.length,
        message: '演示模式：可选合同查询成功',
      },
      statusCode: 200,
    };
  }
  return request({
    url: '/sales-contracts/available',
    method: 'GET',
  });
}

async function listSalesOrders(status) {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    const items = listDemoSalesOrders(status);
    return {
      data: {
        items,
        total: items.length,
        message: '演示模式：订单列表查询成功',
      },
      statusCode: 200,
    };
  }
  const suffix = status ? `?status=${encodeURIComponent(status)}` : '';
  return request({
    url: `/sales-orders${suffix}`,
    method: 'GET',
  });
}

async function createSalesOrderDraft(payload) {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    return {
      data: createDemoSalesOrder(payload),
      statusCode: 200,
    };
  }
  return request({
    url: '/sales-orders',
    method: 'POST',
    data: payload,
  });
}

async function updateSalesOrderDraft(orderId, payload) {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    return {
      data: updateDemoSalesOrder(orderId, payload),
      statusCode: 200,
    };
  }
  return request({
    url: `/sales-orders/${orderId}`,
    method: 'PUT',
    data: payload,
  });
}

async function submitSalesOrder(orderId, comment) {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    return {
      data: submitDemoSalesOrder(orderId, comment),
      statusCode: 200,
    };
  }
  return request({
    url: `/sales-orders/${orderId}/submit`,
    method: 'POST',
    data: { comment },
  });
}

async function getAccessProfile() {
  return request({
    url: '/access/me',
    method: 'GET',
  });
}

async function loginMiniprogramLocal(roleCode) {
  return request({
    url: '/mini-auth/dev-login',
    method: 'POST',
    data: { role_code: roleCode },
    skipAuth: true,
  });
}

async function loginMiniprogramWechat(code) {
  return request({
    url: '/mini-auth/wechat-login',
    method: 'POST',
    data: { code },
    skipAuth: true,
  });
}

async function completeWarehouseOutbound(payload) {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    return {
      data: buildDemoExecResponse('system', payload),
      statusCode: 200,
    };
  }
  const created = await request({
    url: '/outbound-docs/warehouse-confirm',
    method: 'POST',
    data: payload,
  });
  return request({
    url: `/outbound-docs/${created.data.id}/submit`,
    method: 'POST',
    data: {
      actual_qty: payload.actual_qty,
      warehouse_id: payload.warehouse_id,
    },
  });
}

async function completeManualOutbound(payload) {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    return {
      data: buildDemoExecResponse('manual', payload),
      statusCode: 200,
    };
  }
  const created = await request({
    url: '/outbound-docs/manual',
    method: 'POST',
    data: {
      contract_id: payload.contract_id,
      sales_order_id: payload.sales_order_id,
      oil_product_id: payload.oil_product_id,
      manual_ref_no: payload.manual_ref_no,
      actual_qty: payload.actual_qty,
      reason: payload.reason,
    },
  });
  return request({
    url: `/outbound-docs/${created.data.id}/submit`,
    method: 'POST',
    data: {
      actual_qty: payload.actual_qty,
      warehouse_id: payload.warehouse_id,
    },
  });
}

module.exports = {
  completeManualOutbound,
  completeWarehouseOutbound,
  createSalesOrderDraft,
  getAvailableSalesContracts,
  getAccessProfile,
  getLightReportOverview,
  loginMiniprogramLocal,
  loginMiniprogramWechat,
  listSalesOrders,
  submitSalesOrder,
  updateSalesOrderDraft,
};
