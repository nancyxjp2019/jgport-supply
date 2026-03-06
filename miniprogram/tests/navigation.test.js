const test = require('node:test');
const assert = require('node:assert/strict');

const { resolveHomeEntryLabel, resolveHomePath } = require('../utils/navigation');

test('仓库角色默认进入仓库执行回执', () => {
  assert.equal(resolveHomePath('warehouse'), '/pages/exec/index');
  assert.equal(resolveHomeEntryLabel('warehouse'), '进入仓库执行回执');
});

test('非仓库角色默认进入经营快报', () => {
  assert.equal(resolveHomePath('finance'), '/pages/report/index');
  assert.equal(resolveHomeEntryLabel('customer'), '进入经营快报');
});
