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

test('经营快报页会加载轻量报表并高亮来源异常类型', async () => {
  createWxHarness();
  global.getApp = () => ({ globalData: {} });

  const actor = {
    roleCode: 'operations',
    roleLabel: '运营',
  };
  const page = loadPage(require.resolve('../pages/report/index'), {
    [require.resolve('../config/env')]: {
      getRuntimeMode: () => 'local_api',
      getRuntimeModeLabel: () => '本地联调',
    },
    [require.resolve('../utils/api')]: {
      getAccessProfile: async () => ({
        data: {
          role_code: 'operations',
          user_id: 'CODEX-TEST-OPS-USER',
          company_id: 'CODEX-TEST-OPERATOR-COMPANY',
          company_type: 'operator_company',
          client_type: 'miniprogram',
          admin_web_allowed: true,
          miniprogram_allowed: true,
        },
      }),
      getLightReportOverview: async () => ({
        data: {
          metric_version: 'v1',
          snapshot_time: '2026-03-08T10:00:00+08:00',
          sla_status: '正常',
          actual_receipt_today: '650025.00',
          actual_payment_today: '580080.00',
          inbound_qty_today: '100.000',
          outbound_qty_today: '80.000',
          abnormal_count: 3,
          pending_supplement_count: 1,
          validation_failed_count: 1,
          qty_done_not_closed_count: 1,
        },
      }),
    },
    [require.resolve('../utils/session')]: {
      getAccessToken: () => 'CODEX-TEST-OPS-TOKEN',
      initializeSession: () => actor,
      logoutSession: () => undefined,
      updateAccessProfile: () => actor,
    },
  });
  const context = createPageContext(page);

  context.onLoad({
    focusAbnormal: 'qtydone',
    source: 'message',
    sourceDetail: '定位到未关闭合同异常',
  });
  await context.loadOverview();

  assert.equal(context.data.canView, true);
  assert.equal(context.data.metricVersionText, '口径版本 v1');
  assert.equal(context.data.abnormalExpanded, true);
  assert.equal(context.data.abnormalItems.find((item) => item.key === 'qtydone').focused, true);
  assert.equal(context.data.sourceText, '当前通过消息中心进入该页面。');
  assert.equal(context.data.sourceDetailText, '定位到未关闭合同异常');
});

test('客户角色打开经营快报页时仅显示权限边界', async () => {
  createWxHarness();
  global.getApp = () => ({ globalData: {} });

  const actor = {
    roleCode: 'customer',
    roleLabel: '客户',
  };
  const page = loadPage(require.resolve('../pages/report/index'), {
    [require.resolve('../config/env')]: {
      getRuntimeMode: () => 'demo',
      getRuntimeModeLabel: () => '演示模式',
    },
    [require.resolve('../utils/api')]: {
      getAccessProfile: async () => ({ data: {} }),
      getLightReportOverview: async () => ({ data: {} }),
    },
    [require.resolve('../utils/session')]: {
      getAccessToken: () => '',
      initializeSession: () => actor,
      logoutSession: () => undefined,
      updateAccessProfile: () => actor,
    },
  });
  const context = createPageContext(page);

  await context.loadOverview();

  assert.equal(context.data.canView, false);
  assert.equal(context.data.loading, false);
  assert.equal(context.data.roleLabel, '客户');
  assert.equal(context.data.metricCards.length, 0);
});
