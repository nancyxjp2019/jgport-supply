const { getApiBaseUrl, getCurrentEnvironment } = require('./config/env');

App({
  globalData: {
    token: '',
    user: null,
    apiBaseUrl: getApiBaseUrl(),
    environment: getCurrentEnvironment(),
  },

  onLaunch() {
    const token = wx.getStorageSync('token') || '';
    const user = wx.getStorageSync('user') || null;
    this.globalData.token = String(token || '').trim();
    this.globalData.user = user || null;
    this.globalData.apiBaseUrl = getApiBaseUrl();
    this.globalData.environment = getCurrentEnvironment();
  },
});
