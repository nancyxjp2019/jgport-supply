const { getDemoActor, getRuntimeMode, getRuntimeModeLabel } = require('./config/env');

App({
  globalData: {
    runtimeMode: 'demo',
    runtimeLabel: '演示模式',
    user: null,
  },

  onLaunch() {
    this.globalData.runtimeMode = getRuntimeMode();
    this.globalData.runtimeLabel = getRuntimeModeLabel(this.globalData.runtimeMode);
    this.globalData.user = getDemoActor();
  },
});
