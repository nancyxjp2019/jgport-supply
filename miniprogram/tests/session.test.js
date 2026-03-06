const test = require('node:test');
const assert = require('node:assert/strict');

function createStorageHarness() {
  const storage = new Map();
  global.wx = {
    getStorageSync(key) {
      return storage.get(key) || '';
    },
    setStorageSync(key, value) {
      storage.set(key, value);
    },
    removeStorageSync(key) {
      storage.delete(key);
    },
  };
  return storage;
}

test('登录指定角色后会同步到全局会话', () => {
  const storage = createStorageHarness();
  const app = { globalData: {} };
  global.getApp = () => app;
  delete require.cache[require.resolve('../config/env')];
  delete require.cache[require.resolve('../utils/session')];
  const { loginAsDemoRole } = require('../utils/session');
  const actor = loginAsDemoRole('finance');
  assert.equal(storage.get('mini_demo_role_code'), 'finance');
  assert.equal(actor.roleLabel, '财务');
  assert.equal(app.globalData.user.roleCode, 'finance');
});

test('退出会话后会清空当前身份', () => {
  const storage = createStorageHarness();
  storage.set('mini_demo_role_code', 'operations');
  const app = { globalData: {} };
  global.getApp = () => app;
  delete require.cache[require.resolve('../config/env')];
  delete require.cache[require.resolve('../utils/session')];
  const { initializeSession, logoutSession } = require('../utils/session');
  initializeSession();
  logoutSession();
  assert.equal(storage.has('mini_demo_role_code'), false);
  assert.equal(app.globalData.user, null);
});
