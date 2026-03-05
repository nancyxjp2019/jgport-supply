const { bindWithActivation, loginWithCode, setSession } = require('../../utils/auth');

Page({
  data: {
    needActivation: false,
    activationCode: '',
    tempCode: '',
    message: '',
    loading: false,
  },

  onShow() {
    const app = getApp();
    if (app.globalData.token) {
      wx.reLaunch({ url: '/pages/home/index' });
    }
  },

  onActivationCodeInput(e) {
    this.setData({ activationCode: String((e.detail && e.detail.value) || '').trim() });
  },

  onLogin() {
    if (this.data.loading) {
      return;
    }
    this.setData({ loading: true, message: '' });
    wx.login({
      success: async (wxRes) => {
        if (!wxRes.code) {
          this.setData({ loading: false, message: '获取微信登录凭证失败，请重试' });
          return;
        }
        try {
          const res = await loginWithCode(wxRes.code);
          if (res.data && res.data.activation_required) {
            this.setData({
              needActivation: true,
              tempCode: wxRes.code,
              message: '当前账号未激活，请输入激活码完成绑定',
              loading: false,
            });
            return;
          }
          setSession(res.data.user, res.data.access_token);
          wx.reLaunch({ url: '/pages/home/index' });
        } catch (error) {
          this.setData({ message: `登录失败：${error.message}`, loading: false });
          return;
        }
        this.setData({ loading: false });
      },
      fail: () => {
        this.setData({ loading: false, message: '调用微信登录失败，请稍后重试' });
      },
    });
  },

  async onBind() {
    if (!this.data.tempCode) {
      this.setData({ message: '请先点击微信登录' });
      return;
    }
    if (!this.data.activationCode) {
      this.setData({ message: '请输入激活码' });
      return;
    }
    this.setData({ loading: true, message: '' });
    try {
      const res = await bindWithActivation(this.data.tempCode, this.data.activationCode);
      setSession(res.data.user, res.data.access_token);
      wx.reLaunch({ url: '/pages/home/index' });
    } catch (error) {
      this.setData({ message: `激活失败：${error.message}` });
    }
    this.setData({ loading: false });
  },
});
