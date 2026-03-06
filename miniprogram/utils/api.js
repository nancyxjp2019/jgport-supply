const { getRuntimeMode } = require('../config/env');
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
  getAccessProfile,
  getLightReportOverview,
  loginMiniprogramLocal,
  loginMiniprogramWechat,
};
