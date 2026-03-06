const { getRuntimeMode, getRuntimeModeLabel } = require('../../config/env');
const { getAccessProfile, getLightReportOverview } = require('../../utils/api');
const { formatDateTime, formatMoney, formatQty } = require('../../utils/format');
const { resolveEntrySourceMeta, resolveReportFocusKey } = require('../../utils/navigation');
const { getAccessToken, initializeSession, logoutSession, updateAccessProfile } = require('../../utils/session');
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
    focusedAbnormalKey: '',
    isEmpty: false,
    skeletonItems: [1, 2, 3, 4],
    sourceText: '',
    sourceDetailText: '',
  },

  onLoad(options) {
    const sourceMeta = resolveEntrySourceMeta(options);
    this.setData({
      focusedAbnormalKey: resolveReportFocusKey(options && options.focusAbnormal),
      sourceText: sourceMeta.sourceText,
      sourceDetailText: sourceMeta.sourceDetailText,
    });
  },

  onShow() {
    this.loadOverview();
  },

  _decorateAbnormalItems(items) {
    const focusKey = this.data.focusedAbnormalKey;
    return (items || []).map((item) => ({
      ...item,
      focused: Boolean(focusKey) && item.key === focusKey,
    }));
  },

  onPullDownRefresh() {
    this.loadOverview();
  },

  async loadOverview() {
    const app = getApp();
    const runtimeMode = getRuntimeMode();
    let currentUser = initializeSession();
    if (runtimeMode === 'local_api') {
      if (!getAccessToken() || !currentUser) {
        this._redirectToLogin();
        return;
      }
      try {
        const response = await getAccessProfile();
        currentUser = updateAccessProfile(response.data);
      } catch (error) {
        if (Number(error.statusCode || 0) === 401) {
          logoutSession();
          wx.showToast({ title: error.message || '登录状态已失效，请重新登录', icon: 'none' });
          this._redirectToLogin();
          return;
        }
        this.setData({
          loading: false,
          errorMessage: error.message || '读取登录身份失败，请确认本地后端已启动',
          canView: false,
          roleLabel: currentUser ? currentUser.roleLabel : '',
          runtimeLabel: getRuntimeModeLabel(runtimeMode),
          metricVersionText: '口径版本 v1',
          snapshotTimeText: '暂无时间',
          slaStatusText: '正常',
          statusClass: 'status-pill--normal',
          statusText: '身份读取失败',
          overview: null,
          metricCards: [],
          abnormalItems: [],
          abnormalExpanded: Boolean(this.data.focusedAbnormalKey),
          isEmpty: false,
        });
        wx.stopPullDownRefresh();
        return;
      }
    }
    if (!currentUser) {
      this._redirectToLogin();
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
    });

    if (!canView) {
      wx.stopPullDownRefresh();
      return;
    }

    try {
      const response = await getLightReportOverview();
      const overview = response.data;
      const metricCards = buildMetricCards(overview, { formatMoney, formatQty });
      const abnormalItems = this._decorateAbnormalItems(buildAbnormalItems(overview));
      this.setData({
        loading: false,
        overview,
        metricCards,
        abnormalItems,
        metricVersionText: `口径版本 ${overview.metric_version}`,
        snapshotTimeText: formatDateTime(overview.snapshot_time),
        slaStatusText: overview.sla_status || '正常',
        statusClass: resolveStatusClass(overview.sla_status),
        statusText: resolveOverviewStatusText(overview.sla_status),
        abnormalExpanded: Boolean(this.data.focusedAbnormalKey),
        isEmpty: isOverviewEmpty(overview),
      });
    } catch (error) {
      if (Number(error.statusCode || 0) === 401) {
        logoutSession();
        wx.showToast({ title: error.message || '登录状态已失效，请重新登录', icon: 'none' });
        this._redirectToLogin();
        return;
      }
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

  _redirectToLogin() {
    this.setData({
      loading: false,
      errorMessage: '',
      canView: false,
      roleLabel: '',
      runtimeLabel: getRuntimeModeLabel(getRuntimeMode()),
      metricVersionText: '口径版本 v1',
      snapshotTimeText: '暂无时间',
      slaStatusText: '正常',
      statusClass: 'status-pill--normal',
      statusText: '请先登录',
      overview: null,
      metricCards: [],
      abnormalItems: [],
      abnormalExpanded: false,
      isEmpty: false,
    });
    wx.stopPullDownRefresh();
    wx.reLaunch({ url: '/pages/login/index' });
  },
});
