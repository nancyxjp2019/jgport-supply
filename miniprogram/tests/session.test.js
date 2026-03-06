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
  assert.equal(app.globalData.runtimeMode, 'demo');
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

test('切换到本地联调模式会清空旧会话', () => {
  const storage = createStorageHarness();
  storage.set('mini_demo_role_code', 'operations');
  storage.set('mini_access_token', 'CODEX-TEST-TOKEN');
  const app = { globalData: {} };
  global.getApp = () => app;
  delete require.cache[require.resolve('../config/env')];
  delete require.cache[require.resolve('../utils/session')];
  const { setLoginRuntimeMode } = require('../utils/session');
  setLoginRuntimeMode('local_api');
  assert.equal(storage.get('mini_runtime_mode'), 'local_api');
  assert.equal(storage.has('mini_demo_role_code'), false);
  assert.equal(storage.has('mini_access_token'), false);
  assert.equal(app.globalData.user, null);
});

test('保存本地联调会话后可恢复当前身份', () => {
  const storage = createStorageHarness();
  const app = { globalData: {} };
  global.getApp = () => app;
  delete require.cache[require.resolve('../config/env')];
  delete require.cache[require.resolve('../utils/session')];
  const { saveAccessSession, initializeSession, getAccessToken } = require('../utils/session');
  saveAccessSession({
    accessToken: 'CODEX-TEST-BEARER',
    profile: {
      user_id: 'AUTO-TEST-MINI-OPS-001',
      role_code: 'operations',
      company_id: 'AUTO-TEST-OPERATOR-COMPANY',
      company_type: 'operator_company',
      client_type: 'miniprogram',
      admin_web_allowed: true,
      miniprogram_allowed: true,
    },
  });
  storage.set('mini_runtime_mode', 'local_api');
  const actor = initializeSession();
  assert.equal(getAccessToken(), 'CODEX-TEST-BEARER');
  assert.equal(actor.roleCode, 'operations');
  assert.equal(actor.roleLabel, '运营');
  assert.equal(app.globalData.runtimeMode, 'local_api');
});
