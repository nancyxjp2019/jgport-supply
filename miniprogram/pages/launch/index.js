Page({
  data: {
    countdownText: '正在进入 V5 工作台',
  },

  onLoad() {
    this.startDefaultRedirect();
  },

  onUnload() {
    this.clearTimer();
  },

  onHide() {
    this.clearTimer();
  },

  clearTimer() {
    if (!this.redirectTimer) {
      return;
    }
    clearTimeout(this.redirectTimer);
    this.redirectTimer = null;
  },

  startDefaultRedirect() {
    this.clearTimer();
    this.redirectTimer = setTimeout(() => {
      const app = getApp();
      const token = String(app.globalData.token || wx.getStorageSync('token') || '').trim();
      if (token) {
        wx.reLaunch({ url: '/pages/home/index' });
        return;
      }
      wx.reLaunch({ url: '/pages/login/index' });
    }, 1200);
  },

});
