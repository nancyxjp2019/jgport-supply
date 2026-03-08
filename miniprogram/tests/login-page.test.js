const test = require('node:test');
const assert = require('node:assert/strict');

const { createPageContext, loadPage } = require('./page-harness');

function createWxHarness() {
  const calls = {
    reLaunch: [],
    showToast: [],
  };
  global.wx = {
    reLaunch(options) {
      calls.reLaunch.push(options);
    },
    showToast(options) {
      calls.showToast.push(options);
    },
    login(options) {
      options.success({ code: 'WX-CODE-001' });
    },
  };
  return calls;
}

function buildActors() {
  return {
    operations: { roleLabel: '运营' },
    finance: { roleLabel: '财务' },
    admin: { roleLabel: '管理员' },
    customer: { roleLabel: '客户' },
    supplier: { roleLabel: '供应商' },
    warehouse: { roleLabel: '仓库' },
  };
}

test('本地联调登录成功后会跳转到我的待办', async () => {
  const calls = createWxHarness();
  global.getApp = () => ({ globalData: {} });

  let runtimeMode = 'local_api';
  let savedSession = null;
  const page = loadPage(require.resolve('../pages/login/index'), {
    [require.resolve('../config/env')]: {
      DEMO_ACTORS: buildActors(),
      getApiBaseUrl: () => 'http://127.0.0.1:8000/api/v1',
      getRuntimeMode: () => runtimeMode,
      getRuntimeModeLabel: () => '本地联调',
    },
    [require.resolve('../utils/api')]: {
      loginMiniprogramLocal: async (roleCode) => ({
        data: {
          access_token: 'CODEX-TEST-MINI-TOKEN',
          role_code: roleCode,
          company_id: 'CODEX-TEST-OPERATOR-COMPANY',
          company_type: 'operator_company',
          client_type: 'miniprogram',
          admin_web_allowed: true,
          miniprogram_allowed: true,
        },
      }),
      loginMiniprogramWechat: async () => ({ data: {} }),
    },
    [require.resolve('../utils/light-report')]: {
      canViewLightReport: (roleCode) => ['operations', 'finance', 'admin'].includes(roleCode),
    },
    [require.resolve('../utils/navigation')]: {
      resolveHomeEntryLabel: () => '进入我的待办',
      resolveHomePath: () => '/pages/todo/index',
    },
    [require.resolve('../utils/session')]: {
      initializeSession: () => null,
      loginAsDemoRole: () => null,
      logoutSession: () => undefined,
      saveAccessSession: ({ accessToken, profile }) => {
        savedSession = { accessToken, profile };
        return { roleCode: profile.role_code, roleLabel: '运营' };
      },
      setLoginRuntimeMode: (mode) => {
        runtimeMode = mode;
      },
    },
  });
  const context = createPageContext(page);

  context.onShow();
  await context.onLogin({ currentTarget: { dataset: { roleCode: 'operations' } } });

  assert.equal(context.data.runtimeMode, 'local_api');
  assert.equal(context.data.currentRoleLabel, '运营');
  assert.equal(savedSession.accessToken, 'CODEX-TEST-MINI-TOKEN');
  assert.equal(savedSession.profile.role_code, 'operations');
  assert.deepEqual(calls.reLaunch[0], { url: '/pages/todo/index' });
});

test('微信登录未绑定时会展示提示并保留 debug_openid', async () => {
  const calls = createWxHarness();
  global.getApp = () => ({ globalData: {} });

  const page = loadPage(require.resolve('../pages/login/index'), {
    [require.resolve('../config/env')]: {
      DEMO_ACTORS: buildActors(),
      getApiBaseUrl: () => 'http://127.0.0.1:8000/api/v1',
      getRuntimeMode: () => 'wechat_auth',
      getRuntimeModeLabel: () => '微信登录',
    },
    [require.resolve('../utils/api')]: {
      loginMiniprogramLocal: async () => ({ data: {} }),
      loginMiniprogramWechat: async () => ({
        data: {
          binding_required: true,
          message: '当前微信账号未绑定业务角色，请联系管理员',
          debug_openid: 'wx-openid-d01-binding',
        },
      }),
    },
    [require.resolve('../utils/light-report')]: {
      canViewLightReport: (roleCode) => ['operations', 'finance', 'admin'].includes(roleCode),
    },
    [require.resolve('../utils/navigation')]: {
      resolveHomeEntryLabel: () => '进入我的待办',
      resolveHomePath: () => '/pages/todo/index',
    },
    [require.resolve('../utils/session')]: {
      initializeSession: () => null,
      loginAsDemoRole: () => null,
      logoutSession: () => undefined,
      saveAccessSession: () => {
        throw new Error('未绑定账号不应写入会话');
      },
      setLoginRuntimeMode: () => undefined,
    },
  });
  const context = createPageContext(page);

  context.onShow();
  await context.onLogin({ currentTarget: { dataset: { roleCode: 'operations' } } });

  assert.equal(context.data.bindingHint, '当前微信账号未绑定业务角色，请联系管理员');
  assert.equal(context.data.debugOpenId, 'wx-openid-d01-binding');
  assert.equal(calls.reLaunch.length, 0);
  assert.equal(calls.showToast[0].title, '当前微信账号未绑定');
});
