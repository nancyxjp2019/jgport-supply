const test = require('node:test');
const assert = require('node:assert/strict');

const {
  buildExecPageUrl,
  buildOrderPageUrl,
  buildReportPageUrl,
  resolveEntrySourceMeta,
  resolveHomeEntryLabel,
  resolveHomePath,
  resolveReportFocusKey,
} = require('../utils/navigation');

test('仓库角色默认进入我的待办', () => {
  assert.equal(resolveHomePath('warehouse'), '/pages/todo/index');
  assert.equal(resolveHomeEntryLabel('warehouse'), '进入我的待办');
});

test('客户角色默认进入我的待办', () => {
  assert.equal(resolveHomePath('customer'), '/pages/todo/index');
  assert.equal(resolveHomeEntryLabel('customer'), '进入我的待办');
});

test('运营侧角色默认进入我的待办', () => {
  assert.equal(resolveHomePath('finance'), '/pages/todo/index');
  assert.equal(resolveHomeEntryLabel('operations'), '进入我的待办');
});

test('消息深链会统一拼装订单、报表与执行页地址', () => {
  assert.equal(
    buildOrderPageUrl({ tab: 'query', status: '待财务审批', source: 'message', sourceDetail: '定位订单审批进度' }),
    '/pages/order/index?tab=query&status=%E5%BE%85%E8%B4%A2%E5%8A%A1%E5%AE%A1%E6%89%B9&source=message&sourceDetail=%E5%AE%9A%E4%BD%8D%E8%AE%A2%E5%8D%95%E5%AE%A1%E6%89%B9%E8%BF%9B%E5%BA%A6',
  );
  assert.equal(
    buildReportPageUrl({ focusAbnormal: 'failed', source: 'message', sourceDetail: '定位校验失败异常' }),
    '/pages/report/index?focusAbnormal=failed&source=message&sourceDetail=%E5%AE%9A%E4%BD%8D%E6%A0%A1%E9%AA%8C%E5%A4%B1%E8%B4%A5%E5%BC%82%E5%B8%B8',
  );
  assert.equal(
    buildExecPageUrl({ mode: 'manual', source: 'message', sourceDetail: '定位手工补录入口' }),
    '/pages/exec/index?mode=manual&source=message&sourceDetail=%E5%AE%9A%E4%BD%8D%E6%89%8B%E5%B7%A5%E8%A1%A5%E5%BD%95%E5%85%A5%E5%8F%A3',
  );
});

test('来源元信息与报表关注类型会被正确解析', () => {
  assert.deepEqual(resolveEntrySourceMeta({ source: 'message', sourceDetail: '已定位到目标页面' }), {
    sourceText: '当前通过消息中心进入该页面。',
    sourceDetailText: '已定位到目标页面',
  });
  assert.equal(resolveReportFocusKey('qtydone'), 'qtydone');
  assert.equal(resolveReportFocusKey('unknown'), '');
});
