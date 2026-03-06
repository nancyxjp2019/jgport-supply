const { DEMO_ACTORS, getRuntimeModeLabel } = require('../../config/env');
const { canViewLightReport } = require('../../utils/light-report');
const { initializeSession, loginAsDemoRole, logoutSession } = require('../../utils/session');

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
    description: '验证当前页对客户角色的金额信息阻断。',
    companyLabel: '归属：客户公司',
  },
  {
    roleCode: 'supplier',
    description: '验证供应商角色不可查看经营金额汇总。',
    companyLabel: '归属：供应商公司',
  },
  {
    roleCode: 'warehouse',
    description: '验证仓库角色仅保留移动执行能力边界。',
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
    runtimeLabel: '演示模式',
    currentRoleLabel: '',
    roleCards: buildRoleCards(),
  },

  onShow() {
    const currentUser = initializeSession();
    const app = getApp();
    this.setData({
      runtimeLabel: getRuntimeModeLabel((app.globalData && app.globalData.runtimeMode) || 'demo'),
      currentRoleLabel: currentUser ? currentUser.roleLabel : '',
      roleCards: buildRoleCards(),
    });
  },

  onLogin(event) {
    const roleCode = String(event.currentTarget.dataset.roleCode || '').trim();
    let actor = null;
    try {
      actor = loginAsDemoRole(roleCode);
    } catch (error) {
      wx.showToast({
        title: error.message || '角色切换失败',
        icon: 'none',
      });
      return;
    }
    this.setData({
      currentRoleLabel: actor ? actor.roleLabel : '',
    });
    wx.reLaunch({ url: '/pages/report/index' });
  },

  onEnterReport() {
    wx.reLaunch({ url: '/pages/report/index' });
  },

  onLogout() {
    logoutSession();
    this.setData({
      currentRoleLabel: '',
    });
    wx.showToast({ title: '已清除当前身份', icon: 'none' });
  },
});
