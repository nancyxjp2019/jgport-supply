const {
  clearDemoRoleCode,
  getDemoActor,
  getRuntimeMode,
  getRuntimeModeLabel,
  setDemoRoleCode,
  setRuntimeMode,
} = require('../config/env');

const STORAGE_ACCESS_TOKEN_KEY = 'mini_access_token';
const STORAGE_ACCESS_PROFILE_KEY = 'mini_access_profile';

function getAppInstance() {
  if (typeof getApp !== 'function') {
    return { globalData: {} };
  }
  const app = getApp();
  app.globalData = app.globalData || {};
  return app;
}

function syncAppGlobal(actor) {
  const app = getAppInstance();
  app.globalData.runtimeMode = getRuntimeMode();
  app.globalData.runtimeLabel = getRuntimeModeLabel(app.globalData.runtimeMode);
  app.globalData.user = actor || null;
}

function initializeSession() {
  const actor = getRuntimeMode() === 'local_api' ? getStoredAccessActor() : getDemoActor();
  syncAppGlobal(actor);
  return actor;
}

function loginAsDemoRole(roleCode) {
  setRuntimeMode('demo');
  clearAccessSession();
  setDemoRoleCode(roleCode);
  const actor = getDemoActor();
  syncAppGlobal(actor);
  return actor;
}

function setLoginRuntimeMode(mode) {
  setRuntimeMode(mode);
  clearDemoRoleCode();
  clearAccessSession();
  syncAppGlobal(null);
}

function getAccessToken() {
  if (typeof wx === 'undefined' || typeof wx.getStorageSync !== 'function') {
    return '';
  }
  return String(wx.getStorageSync(STORAGE_ACCESS_TOKEN_KEY) || '').trim();
}

function adaptAccessProfile(profile) {
  if (!profile) {
    return null;
  }
  return {
    userId: String(profile.user_id || ''),
    roleCode: String(profile.role_code || ''),
    roleLabel: require('./light-report').getRoleLabel(profile.role_code),
    companyId: profile.company_id || '',
    companyType: String(profile.company_type || ''),
    clientType: String(profile.client_type || ''),
    adminWebAllowed: Boolean(profile.admin_web_allowed),
    miniprogramAllowed: Boolean(profile.miniprogram_allowed),
  };
}

function getStoredAccessActor() {
  if (typeof wx === 'undefined' || typeof wx.getStorageSync !== 'function') {
    return null;
  }
  return adaptAccessProfile(wx.getStorageSync(STORAGE_ACCESS_PROFILE_KEY));
}

function saveAccessSession({ accessToken, profile }) {
  const actor = adaptAccessProfile(profile);
  if (!accessToken || !actor) {
    throw new Error('本地联调登录结果无效');
  }
  if (typeof wx !== 'undefined' && typeof wx.setStorageSync === 'function') {
    wx.setStorageSync(STORAGE_ACCESS_TOKEN_KEY, String(accessToken).trim());
    wx.setStorageSync(STORAGE_ACCESS_PROFILE_KEY, profile);
  }
  syncAppGlobal(actor);
  return actor;
}

function updateAccessProfile(profile) {
  const actor = adaptAccessProfile(profile);
  if (!actor) {
    return null;
  }
  if (typeof wx !== 'undefined' && typeof wx.setStorageSync === 'function') {
    wx.setStorageSync(STORAGE_ACCESS_PROFILE_KEY, profile);
  }
  syncAppGlobal(actor);
  return actor;
}

function clearAccessSession() {
  if (typeof wx !== 'undefined' && typeof wx.removeStorageSync === 'function') {
    wx.removeStorageSync(STORAGE_ACCESS_TOKEN_KEY);
    wx.removeStorageSync(STORAGE_ACCESS_PROFILE_KEY);
  }
}

function logoutSession() {
  clearDemoRoleCode();
  clearAccessSession();
  syncAppGlobal(null);
}

module.exports = {
  getAccessToken,
  getStoredAccessActor,
  initializeSession,
  loginAsDemoRole,
  logoutSession,
  saveAccessSession,
  setLoginRuntimeMode,
  updateAccessProfile,
};
