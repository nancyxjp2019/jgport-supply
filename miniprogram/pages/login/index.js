const { DEMO_ACTORS, getApiBaseUrl, getRuntimeMode, getRuntimeModeLabel } = require('../../config/env');
const { loginMiniprogramLocal, loginMiniprogramWechat } = require('../../utils/api');
const { canViewLightReport } = require('../../utils/light-report');
const { resolveHomeEntryLabel, resolveHomePath } = require('../../utils/navigation');
const { initializeSession, loginAsDemoRole, logoutSession, saveAccessSession, setLoginRuntimeMode } = require('../../utils/session');

const ROLE_CARD_CONFIG = [
  {
    roleCode: 'operations',
    description: '查看经营快报、履约异常和经营概览。',
    companyLabel: '归属：运营商公司',
  },
  {
    roleCode: 'finance',
    description: '查看实收实付、异常提醒和闭环风险。',
    companyLabel: '归属：运营商公司',
  },
  {
    roleCode: 'admin',
    description: '验证管理后台与小程序的角色边界。',
    companyLabel: '归属：运营商公司',
  },
  {
    roleCode: 'customer',
    description: '进入订单发起与查询，按合同创建并提交订单。',
    companyLabel: '归属：客户公司',
  },
  {
    roleCode: 'supplier',
    description: '验证供应商角色不可查看经营金额汇总。',
    companyLabel: '归属：供应商公司',
  },
  {
    roleCode: 'warehouse',
    description: '进入仓库执行回执，提交正常回执或手工补录。',
    companyLabel: '归属：仓库公司',
  },
];

function buildRoleCards() {
  return ROLE_CARD_CONFIG.map((item) => ({
    ...item,
    roleLabel: DEMO_ACTORS[item.roleCode].roleLabel,
    accessText: canViewLightReport(item.roleCode) ? '快报可见' : '快报阻断',
    accessClass: canViewLightReport(item.roleCode) ? 'status-pill--allow' : 'status-pill--deny',
  }));
}

Page({
  data: {
    runtimeMode: 'demo',
    runtimeLabel: '演示模式',
    currentRoleLabel: '',
    currentHomeLabel: '进入经营快报',
    apiBaseUrl: '',
    bindingHint: '',
    debugOpenId: '',
    roleCards: buildRoleCards(),
  },

  onShow() {
    const currentUser = initializeSession();
    const runtimeMode = getRuntimeMode();
    this.setData({
      runtimeMode,
      runtimeLabel: getRuntimeModeLabel(runtimeMode),
      currentRoleLabel: currentUser ? currentUser.roleLabel : '',
      currentHomeLabel: currentUser ? resolveHomeEntryLabel(currentUser.roleCode) : '进入经营快报',
      apiBaseUrl: getApiBaseUrl(),
      bindingHint: '',
      debugOpenId: '',
      roleCards: buildRoleCards(),
    });
  },

  onSelectMode(event) {
    const mode = String(event.currentTarget.dataset.mode || '').trim();
    setLoginRuntimeMode(mode);
    this.setData({
      runtimeMode: getRuntimeMode(),
      runtimeLabel: getRuntimeModeLabel(getRuntimeMode()),
      currentRoleLabel: '',
      currentHomeLabel: '进入经营快报',
      apiBaseUrl: getApiBaseUrl(),
      bindingHint: '',
      debugOpenId: '',
    });
  },

  async onLogin(event) {
    const roleCode = String(event.currentTarget.dataset.roleCode || '').trim();
    let actor = null;
    try {
      if (this.data.runtimeMode === 'local_api') {
        const response = await loginMiniprogramLocal(roleCode);
        actor = saveAccessSession({
          accessToken: response.data.access_token,
          profile: response.data,
        });
      } else if (this.data.runtimeMode === 'wechat_auth') {
        const code = await this.requestWechatCode();
        const response = await loginMiniprogramWechat(code);
        if (response.data.binding_required) {
          this.setData({
            bindingHint: response.data.message || '当前微信账号未绑定业务角色，请联系管理员',
            debugOpenId: response.data.debug_openid || '',
            currentRoleLabel: '',
          });
          wx.showToast({
            title: '当前微信账号未绑定',
            icon: 'none',
          });
          return;
        }
        actor = saveAccessSession({
          accessToken: response.data.access_token,
          profile: response.data,
        });
      } else {
        actor = loginAsDemoRole(roleCode);
      }
    } catch (error) {
      wx.showToast({
        title: error.message || '登录失败，请稍后重试',
        icon: 'none',
      });
      return;
    }
    this.setData({
      currentRoleLabel: actor ? actor.roleLabel : '',
      currentHomeLabel: actor ? resolveHomeEntryLabel(actor.roleCode) : '进入经营快报',
      bindingHint: '',
      debugOpenId: '',
    });
    wx.reLaunch({ url: resolveHomePath(actor ? actor.roleCode : '') });
  },

  onEnterReport() {
    const currentUser = initializeSession();
    wx.reLaunch({ url: resolveHomePath(currentUser ? currentUser.roleCode : '') });
  },

  onLogout() {
    logoutSession();
    this.setData({
      currentRoleLabel: '',
      currentHomeLabel: '进入经营快报',
      bindingHint: '',
      debugOpenId: '',
    });
    wx.showToast({ title: '已清除当前身份', icon: 'none' });
  },

  requestWechatCode() {
    return new Promise((resolve, reject) => {
      if (typeof wx === 'undefined' || typeof wx.login !== 'function') {
        reject({ message: '当前环境不支持微信登录，请在微信开发者工具中重试' });
        return;
      }
      wx.login({
        success: (result) => {
          if (!result.code) {
            reject({ message: '获取微信登录凭证失败，请重试' });
            return;
          }
          resolve(result.code);
        },
        fail: (error) => {
          reject({ message: error.errMsg || '调用微信登录失败，请稍后重试' });
        },
      });
    });
  },
});
