const test = require('node:test');
const assert = require('node:assert/strict');

const { createPageContext, loadPage } = require('./page-harness');

function createWxHarness() {
  const calls = {
    reLaunch: [],
    showToast: [],
    stopPullDownRefresh: 0,
  };
  global.wx = {
    reLaunch(options) {
      calls.reLaunch.push(options);
    },
    showToast(options) {
      calls.showToast.push(options);
    },
    stopPullDownRefresh() {
      calls.stopPullDownRefresh += 1;
    },
  };
  return calls;
}

test('供应商待办页会加载采购订单摘要与快捷入口', async () => {
  createWxHarness();
  global.getApp = () => ({ globalData: {} });

  const actor = {
    roleCode: 'supplier',
    roleLabel: '供应商',
  };
  const purchaseOrders = [
    {
      id: 3001,
      order_no: 'PO-001',
      source_sales_order_no: 'SO-001',
      status: '待供应商确认',
      oil_product_id: 'OIL-92',
      qty_ordered: '12.500',
      payable_amount: '8200.50',
      zero_pay_exception_flag: false,
      created_at: '2026-03-08T09:00:00+08:00',
    },
    {
      id: 3002,
      order_no: 'PO-002',
      source_sales_order_no: 'SO-002',
      status: '供应商已确认',
      oil_product_id: 'OIL-95',
      qty_ordered: '8.000',
      payable_amount: '0.00',
      zero_pay_exception_flag: true,
      created_at: '2026-03-07T09:00:00+08:00',
    },
  ];
  const page = loadPage(require.resolve('../pages/todo/index'), {
    [require.resolve('../config/env')]: {
      getRuntimeMode: () => 'local_api',
      getRuntimeModeLabel: () => '本地联调',
    },
    [require.resolve('../utils/api')]: {
      getAccessProfile: async () => ({
        data: {
          role_code: 'supplier',
          user_id: 'CODEX-TEST-SUPPLIER-USER',
          company_id: 'CODEX-TEST-SUPPLIER-COMPANY',
          company_type: 'supplier_company',
          client_type: 'miniprogram',
          admin_web_allowed: false,
          miniprogram_allowed: true,
        },
      }),
      getLightReportOverview: async () => ({ data: {} }),
      listSalesOrders: async () => ({ data: { items: [] } }),
      listSupplierPurchaseOrders: async () => ({
        data: {
          items: purchaseOrders,
          total: purchaseOrders.length,
        },
      }),
    },
    [require.resolve('../utils/session')]: {
      getAccessToken: () => 'CODEX-TEST-SUPPLIER-TOKEN',
      initializeSession: () => actor,
      logoutSession: () => undefined,
      updateAccessProfile: () => actor,
    },
  });
  const context = createPageContext(page);

  await context.loadPage();

  assert.equal(context.data.loading, false);
  assert.equal(context.data.todoMode, 'supplier');
  assert.equal(context.data.roleLabel, '供应商');
  assert.equal(context.data.summaryCards.length, 4);
  assert.equal(context.data.todoItems[0].orderNo, 'PO-001');
  assert.equal(context.data.quickActions[0].url, '/pages/supplier-purchase/index');
  assert.equal(context.data.quickActions[1].url, '/pages/msg/index');
});
