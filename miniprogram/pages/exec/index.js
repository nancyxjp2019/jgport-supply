const { getRuntimeMode, getRuntimeModeLabel } = require('../../config/env');
const { completeManualOutbound, completeWarehouseOutbound, getAccessProfile } = require('../../utils/api');
const { formatDateTime } = require('../../utils/format');
const { getRoleLabel } = require('../../utils/light-report');
const { resolveHomePath } = require('../../utils/navigation');
const { getAccessToken, initializeSession, logoutSession, updateAccessProfile } = require('../../utils/session');
const {
  buildExecSummary,
  buildManualOutboundPayload,
  buildWarehouseConfirmPayload,
  resolveDefaultWarehouseId,
} = require('../../utils/warehouse-exec');

function buildInitialForm() {
  return {
    contractId: '',
    salesOrderId: '',
    sourceTicketNo: '',
    actualQty: '',
    warehouseId: resolveDefaultWarehouseId(),
  };
}

function buildInitialManualForm() {
  return {
    contractId: '',
    salesOrderId: '',
    oilProductId: '',
    manualRefNo: '',
    actualQty: '',
    reason: '',
    warehouseId: resolveDefaultWarehouseId(),
  };
}

Page({
  data: {
    loading: true,
    submitting: false,
    allowed: false,
    errorMessage: '',
    roleLabel: '',
    runtimeLabel: '演示模式',
    activeMode: 'system',
    systemForm: buildInitialForm(),
    manualForm: buildInitialManualForm(),
    fieldErrors: {},
    latestResult: null,
    latestSummary: [],
    latestSubmittedAtText: '',
  },

  onShow() {
    this.loadPage();
  },

  async loadPage() {
    const runtimeMode = getRuntimeMode();
    let currentUser = initializeSession();
    if (['local_api', 'wechat_auth'].includes(runtimeMode)) {
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
          allowed: false,
          errorMessage: error.message || '读取登录身份失败，请确认本地后端已启动',
          roleLabel: currentUser ? currentUser.roleLabel : '',
          runtimeLabel: getRuntimeModeLabel(runtimeMode),
        });
        return;
      }
    }
    if (!currentUser) {
      this._redirectToLogin();
      return;
    }

    const roleLabel = getRoleLabel(currentUser.roleCode);
    const allowed = currentUser.roleCode === 'warehouse';
    this.setData({
      loading: false,
      allowed,
      errorMessage: '',
      roleLabel,
      runtimeLabel: getRuntimeModeLabel(runtimeMode),
    });
  },

  onSwitchMode(event) {
    this.setData({
      activeMode: String(event.currentTarget.dataset.mode || 'system'),
      fieldErrors: {},
      errorMessage: '',
    });
  },

  onFieldInput(event) {
    const mode = String(event.currentTarget.dataset.mode || 'system');
    const field = String(event.currentTarget.dataset.field || '').trim();
    const value = event.detail.value;
    if (!field) {
      return;
    }
    const targetKey = mode === 'manual' ? 'manualForm' : 'systemForm';
    this.setData({
      [`${targetKey}.${field}`]: value,
      [`fieldErrors.${field}`]: '',
    });
  },

  async onSubmit() {
    if (!this.data.allowed || this.data.submitting) {
      return;
    }

    const mode = this.data.activeMode;
    const validation = mode === 'manual'
      ? buildManualOutboundPayload(this.data.manualForm)
      : buildWarehouseConfirmPayload(this.data.systemForm);
    if (!validation.isValid) {
      this.setData({ fieldErrors: validation.errors });
      wx.showToast({ title: '请先补齐必填信息', icon: 'none' });
      return;
    }

    this.setData({
      submitting: true,
      errorMessage: '',
      fieldErrors: {},
    });
    try {
      const response = mode === 'manual'
        ? await completeManualOutbound(validation.payload)
        : await completeWarehouseOutbound(validation.payload);
      this.setData({
        latestResult: response.data,
        latestSummary: buildExecSummary(response.data, mode),
        latestSubmittedAtText: formatDateTime(response.data.submitted_at),
        systemForm: mode === 'system'
          ? { ...buildInitialForm(), warehouseId: this.data.systemForm.warehouseId }
          : this.data.systemForm,
        manualForm: mode === 'manual'
          ? { ...buildInitialManualForm(), warehouseId: this.data.manualForm.warehouseId }
          : this.data.manualForm,
      });
      wx.showToast({ title: '执行回执已提交', icon: 'success' });
    } catch (error) {
      this.setData({
        errorMessage: error.message || '执行回执提交失败，请稍后重试',
      });
      wx.showToast({ title: error.message || '提交失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },

  onReset() {
    this.setData({
      errorMessage: '',
      fieldErrors: {},
      systemForm: buildInitialForm(),
      manualForm: buildInitialManualForm(),
      latestResult: null,
      latestSummary: [],
      latestSubmittedAtText: '',
    });
  },

  onOpenDefaultPage() {
    const currentUser = initializeSession();
    wx.reLaunch({ url: resolveHomePath(currentUser ? currentUser.roleCode : '') });
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
      allowed: false,
      errorMessage: '',
      roleLabel: '',
      runtimeLabel: getRuntimeModeLabel(getRuntimeMode()),
      latestResult: null,
      latestSummary: [],
      latestSubmittedAtText: '',
    });
    wx.reLaunch({ url: '/pages/login/index' });
  },
});
