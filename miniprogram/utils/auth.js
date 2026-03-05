const { request } = require('./request');

function setSession(user, token) {
  const app = getApp();
  app.globalData.user = user;
  app.globalData.token = token;
  wx.setStorageSync('user', user);
  wx.setStorageSync('token', token);
}

function clearSession() {
  const app = getApp();
  app.globalData.user = null;
  app.globalData.token = '';
  wx.removeStorageSync('user');
  wx.removeStorageSync('token');
}

function loginWithCode(code) {
  return request({
    url: '/auth/wechat/login',
    method: 'POST',
    data: { code },
    withAuth: false,
  });
}

function bindWithActivation(code, activationCode) {
  return request({
    url: '/auth/wechat/bind',
    method: 'POST',
    data: {
      code,
      activation_code: activationCode,
    },
    withAuth: false,
  });
}

function fetchMe() {
  return request({
    url: '/auth/me',
    method: 'GET',
  });
}

module.exports = {
  bindWithActivation,
  clearSession,
  fetchMe,
  loginWithCode,
  setSession,
};
