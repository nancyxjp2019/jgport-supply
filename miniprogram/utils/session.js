const { clearDemoRoleCode, getDemoActor, getRuntimeMode, getRuntimeModeLabel, setDemoRoleCode } = require('../config/env');

function syncAppGlobal(actor) {
  const app = getApp();
  app.globalData.runtimeMode = getRuntimeMode();
  app.globalData.runtimeLabel = getRuntimeModeLabel(app.globalData.runtimeMode);
  app.globalData.user = actor || null;
}

function initializeSession() {
  const actor = getDemoActor();
  syncAppGlobal(actor);
  return actor;
}

function loginAsDemoRole(roleCode) {
  setDemoRoleCode(roleCode);
  const actor = getDemoActor();
  syncAppGlobal(actor);
  return actor;
}

function logoutSession() {
  clearDemoRoleCode();
  syncAppGlobal(null);
}

module.exports = {
  initializeSession,
  loginAsDemoRole,
  logoutSession,
};
