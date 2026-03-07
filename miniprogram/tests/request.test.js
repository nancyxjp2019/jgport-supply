const test = require('node:test');
const assert = require('node:assert/strict');

function createStorageHarness() {
  const storage = new Map();
  return {
    get(key) {
      return storage.get(key);
    },
    has(key) {
      return storage.has(key);
    },
    set(key, value) {
      storage.set(key, value);
    },
    delete(key) {
      storage.delete(key);
    },
  };
}

function installWxHarness(sequence, storage) {
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
    request(options) {
      const current = sequence.shift();
      if (!current) {
        throw new Error('未配置对应的请求桩');
      }
      if (current.expectPath) {
        assert.match(options.url, new RegExp(`${current.expectPath}$`));
      }
      if (current.expectToken) {
        assert.equal(options.header.Authorization, `Bearer ${current.expectToken}`);
      }
      process.nextTick(() => {
        if (current.type === 'fail') {
          options.fail({ errMsg: current.errMsg || 'network fail' });
          return;
        }
        options.success({
          statusCode: current.statusCode,
          data: current.data,
        });
      });
    },
  };
}

function clearModuleCache() {
  delete require.cache[require.resolve('../config/env')];
  delete require.cache[require.resolve('../utils/light-report')];
  delete require.cache[require.resolve('../utils/session')];
  delete require.cache[require.resolve('../utils/request')];
}

test('访问令牌过期后会自动续期并重试原请求', async () => {
  const storage = createStorageHarness();
  storage.set('mini_runtime_mode', 'local_api');
  storage.set('mini_access_token', 'CODEX-TEST-OLD-TOKEN');
  storage.set('mini_access_profile', {
    user_id: 'AUTO-TEST-MINI-OPS-001',
    role_code: 'operations',
    company_id: 'AUTO-TEST-OPERATOR-COMPANY',
    company_type: 'operator_company',
    client_type: 'miniprogram',
    admin_web_allowed: true,
    miniprogram_allowed: true,
  });
  const app = { globalData: {} };
  global.getApp = () => app;

  const sequence = [
    {
      expectPath: '/reports/light/overview',
      expectToken: 'CODEX-TEST-OLD-TOKEN',
      statusCode: 401,
      data: { detail: '登录令牌已过期，请重新登录' },
    },
    {
      expectPath: '/access/session/refresh',
      expectToken: 'CODEX-TEST-OLD-TOKEN',
      statusCode: 200,
      data: {
        access_token: 'CODEX-TEST-NEW-TOKEN',
        token_type: 'Bearer',
        expires_in_seconds: 7200,
        user_id: 'AUTO-TEST-MINI-OPS-001',
        role_code: 'operations',
        company_id: 'AUTO-TEST-OPERATOR-COMPANY',
        company_type: 'operator_company',
        client_type: 'miniprogram',
        admin_web_allowed: true,
        miniprogram_allowed: true,
        message: '会话续期成功',
      },
    },
    {
      expectPath: '/reports/light/overview',
      expectToken: 'CODEX-TEST-NEW-TOKEN',
      statusCode: 200,
      data: { message: 'ok' },
    },
  ];
  installWxHarness(sequence, storage);
  clearModuleCache();
  const { request } = require('../utils/request');

  const response = await request({
    url: '/reports/light/overview',
    method: 'GET',
  });
  assert.equal(response.statusCode, 200);
  assert.equal(response.data.message, 'ok');
  assert.equal(storage.get('mini_access_token'), 'CODEX-TEST-NEW-TOKEN');
  assert.equal(app.globalData.user.roleCode, 'operations');
  assert.equal(sequence.length, 0);
});

test('续期失败时会清空会话并返回失败信息', async () => {
  const storage = createStorageHarness();
  storage.set('mini_runtime_mode', 'local_api');
  storage.set('mini_access_token', 'CODEX-TEST-EXPIRED-TOKEN');
  storage.set('mini_access_profile', {
    user_id: 'AUTO-TEST-MINI-FIN-001',
    role_code: 'finance',
    company_id: 'AUTO-TEST-OPERATOR-COMPANY',
    company_type: 'operator_company',
    client_type: 'miniprogram',
    admin_web_allowed: true,
    miniprogram_allowed: true,
  });
  const app = { globalData: { user: { roleCode: 'finance' } } };
  global.getApp = () => app;

  const sequence = [
    {
      expectPath: '/reports/light/overview',
      expectToken: 'CODEX-TEST-EXPIRED-TOKEN',
      statusCode: 401,
      data: { detail: '登录令牌已过期，请重新登录' },
    },
    {
      expectPath: '/access/session/refresh',
      expectToken: 'CODEX-TEST-EXPIRED-TOKEN',
      statusCode: 403,
      data: { detail: '当前角色不允许在该端续期会话' },
    },
  ];
  installWxHarness(sequence, storage);
  clearModuleCache();
  const { request } = require('../utils/request');

  await assert.rejects(
    () =>
      request({
        url: '/reports/light/overview',
        method: 'GET',
      }),
    (error) => {
      assert.equal(error.statusCode, 403);
      assert.equal(error.message, '当前角色不允许在该端续期会话');
      return true;
    },
  );
  assert.equal(storage.has('mini_access_token'), false);
  assert.equal(storage.has('mini_access_profile'), false);
  assert.equal(app.globalData.user, null);
});
