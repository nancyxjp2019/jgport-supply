const test = require('node:test');
const assert = require('node:assert/strict');

const { resolveHomeEntryLabel, resolveHomePath } = require('../utils/navigation');

test('仓库角色默认进入仓库执行回执', () => {
  assert.equal(resolveHomePath('warehouse'), '/pages/exec/index');
  assert.equal(resolveHomeEntryLabel('warehouse'), '进入仓库执行回执');
});

test('客户角色默认进入订单发起与查询', () => {
  assert.equal(resolveHomePath('customer'), '/pages/order/index');
  assert.equal(resolveHomeEntryLabel('customer'), '进入订单发起与查询');
});

test('非仓库非客户角色默认进入经营快报', () => {
  assert.equal(resolveHomePath('finance'), '/pages/report/index');
  assert.equal(resolveHomeEntryLabel('operations'), '进入经营快报');
});
