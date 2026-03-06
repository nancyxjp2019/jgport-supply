const test = require('node:test');
const assert = require('node:assert/strict');

const { resolveHomeEntryLabel, resolveHomePath } = require('../utils/navigation');

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
