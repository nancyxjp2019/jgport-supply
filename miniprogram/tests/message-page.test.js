const test = require('node:test');
const assert = require('node:assert/strict');

const { createPageContext, loadPage } = require('./page-harness');

function createWxHarness() {
  const storage = new Map();
  const calls = {
    navigateTo: [],
    reLaunch: [],
    showToast: [],
    stopPullDownRefresh: 0,
  };
  global.wx = {
    getStorageSync(key) {
      return storage.get(key) || [];
    },
    setStorageSync(key, value) {
      storage.set(key, value);
    },
    navigateTo(options) {
      calls.navigateTo.push(options);
    },
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
  return { calls, storage };
}

test('消息中心会加载财务消息、支持打开消息并全部标记已读', async () => {
  const { calls, storage } = createWxHarness();
  global.getApp = () => ({ globalData: {} });

  const actor = {
    roleCode: 'finance',
    roleLabel: '财务',
  };
  const page = loadPage(require.resolve('../pages/msg/index'), {
    [require.resolve('../config/env')]: {
      getRuntimeMode: () => 'local_api',
      getRuntimeModeLabel: () => '本地联调',
    },
    [require.resolve('../utils/api')]: {
      getAccessProfile: async () => ({
        data: {
          role_code: 'finance',
          user_id: 'CODEX-TEST-FINANCE-USER',
          company_id: 'CODEX-TEST-OPERATOR-COMPANY',
          company_type: 'operator_company',
          client_type: 'miniprogram',
          admin_web_allowed: true,
          miniprogram_allowed: true,
        },
      }),
      getLightReportOverview: async () => ({
        data: {
          pending_supplement_count: 2,
          validation_failed_count: 1,
          qty_done_not_closed_count: 0,
          snapshot_time: '2026-03-08T10:00:00+08:00',
        },
      }),
      listSalesOrders: async () => ({ data: { items: [] } }),
      listSupplierPurchaseOrders: async () => ({ data: { items: [] } }),
    },
    [require.resolve('../utils/session')]: {
      getAccessToken: () => 'CODEX-TEST-FINANCE-TOKEN',
      initializeSession: () => actor,
      logoutSession: () => undefined,
      updateAccessProfile: () => actor,
    },
  });
  const context = createPageContext(page);

  await context.loadPage();
  assert.equal(context.data.messages.length, 2);
  assert.equal(context.data.unreadCount, 2);

  context.onOpenMessage({
    currentTarget: {
      dataset: {
        key: context.data.messages[0].key,
        url: context.data.messages[0].actionUrl,
      },
    },
  });
  assert.equal(calls.navigateTo.length, 1);
  assert.equal(context.data.unreadCount, 1);

  context.onMarkAllRead();
  assert.equal(context.data.unreadCount, 0);
  assert.deepEqual(storage.get('mini_message_read_keys').sort(), context.data.messages.map((item) => item.key).sort());
  assert.equal(calls.showToast.at(-1).title, '已全部标记为已读');
});
