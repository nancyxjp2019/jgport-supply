const { getDemoActor, getRuntimeModeLabel } = require('../../config/env');
const { getLightReportOverview } = require('../../utils/api');
const { formatDateTime, formatMoney, formatQty } = require('../../utils/format');
const { logoutSession } = require('../../utils/session');
const {
  buildAbnormalItems,
  buildMetricCards,
  canViewLightReport,
  getRoleLabel,
  isOverviewEmpty,
  resolveOverviewStatusText,
  resolveStatusClass,
} = require('../../utils/light-report');

Page({
  data: {
    loading: true,
    errorMessage: '',
    canView: true,
    roleLabel: '',
    runtimeLabel: '演示模式',
    metricVersionText: '口径版本 v1',
    snapshotTimeText: '暂无时间',
    slaStatusText: '正常',
    statusClass: 'status-pill--normal',
    statusText: '数据已更新',
    overview: null,
    metricCards: [],
    abnormalItems: [],
    abnormalExpanded: false,
    isEmpty: false,
    skeletonItems: [1, 2, 3, 4],
  },

  onShow() {
    this.loadOverview();
  },

  onPullDownRefresh() {
    this.loadOverview();
  },

  async loadOverview() {
    const app = getApp();
    const currentUser = getDemoActor();
    if (app && app.globalData) {
      app.globalData.user = currentUser;
    }
    const runtimeMode = (app && app.globalData && app.globalData.runtimeMode) || 'demo';
    if (!currentUser) {
      this.setData({
        loading: false,
        errorMessage: '',
        canView: false,
        roleLabel: '',
        runtimeLabel: getRuntimeModeLabel(runtimeMode),
        overview: null,
        metricCards: [],
        abnormalItems: [],
        abnormalExpanded: false,
        isEmpty: false,
      });
      wx.stopPullDownRefresh();
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    const roleLabel = getRoleLabel(currentUser.roleCode);
    const canView = canViewLightReport(currentUser.roleCode);
    this.setData({
      loading: canView,
      errorMessage: '',
      canView,
      roleLabel,
      runtimeLabel: getRuntimeModeLabel(runtimeMode),
      overview: null,
      metricCards: [],
      abnormalItems: [],
      abnormalExpanded: false,
      isEmpty: false,
    });

    if (!canView) {
      wx.stopPullDownRefresh();
      return;
    }

    try {
      const response = await getLightReportOverview();
      const overview = response.data;
      const metricCards = buildMetricCards(overview, { formatMoney, formatQty });
      this.setData({
        loading: false,
        overview,
        metricCards,
        abnormalItems: buildAbnormalItems(overview),
        metricVersionText: `口径版本 ${overview.metric_version}`,
        snapshotTimeText: formatDateTime(overview.snapshot_time),
        slaStatusText: overview.sla_status || '正常',
        statusClass: resolveStatusClass(overview.sla_status),
        statusText: resolveOverviewStatusText(overview.sla_status),
        isEmpty: isOverviewEmpty(overview),
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '轻量报表加载失败，请稍后重试',
      });
    }
    wx.stopPullDownRefresh();
  },

  onToggleAbnormalDetail() {
    if (!this.data.overview) {
      return;
    }
    this.setData({
      abnormalExpanded: !this.data.abnormalExpanded,
    });
  },

  onSwitchRole() {
    wx.reLaunch({ url: '/pages/login/index' });
  },

  onLogout() {
    logoutSession();
    wx.reLaunch({ url: '/pages/login/index' });
  },
});
