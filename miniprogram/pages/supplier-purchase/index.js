const { getRuntimeMode, getRuntimeModeLabel } = require('../../config/env');
const { getAccessProfile, getSupplierPurchaseOrderDetail, listSupplierPurchaseOrders } = require('../../utils/api');
const { formatDateTime, formatMoney, formatQty } = require('../../utils/format');
const { getRoleLabel } = require('../../utils/light-report');
const { resolveEntrySourceMeta, resolveHomePath } = require('../../utils/navigation');
const { getAccessToken, initializeSession, logoutSession, updateAccessProfile } = require('../../utils/session');
const {
  buildSupplierPreparationHints,
  buildSupplierSummaryCards,
  resolvePurchaseOrderStatusClass,
} = require('../../utils/supplier-purchase');

function buildInitialState() {
  return {
    loading: true,
    detailLoading: false,
    allowed: false,
    errorMessage: '',
    detailErrorMessage: '',
    roleLabel: '',
    runtimeLabel: '演示模式',
    sourceText: '',
    sourceDetailText: '',
    summaryCards: [],
    orders: [],
    selectedOrderId: 0,
    selectedOrder: null,
    emptyText: '当前暂无可查看的采购订单。',
  };
}

Page({
  data: buildInitialState(),

  onLoad(options) {
    const sourceMeta = resolveEntrySourceMeta(options);
    const selectedOrderId = Number((options && options.orderId) || 0);
    this.setData({
      selectedOrderId,
      sourceText: sourceMeta.sourceText,
      sourceDetailText: sourceMeta.sourceDetailText,
    });
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
          ...buildInitialState(),
          loading: false,
          errorMessage: error.message || '读取登录身份失败，请确认本地后端已启动',
          roleLabel: currentUser ? currentUser.roleLabel : '',
          runtimeLabel: getRuntimeModeLabel(runtimeMode),
          sourceText: this.data.sourceText,
          sourceDetailText: this.data.sourceDetailText,
          selectedOrderId: this.data.selectedOrderId,
        });
        return;
      }
    }
    if (!currentUser) {
      this._redirectToLogin();
      return;
    }

    const allowed = currentUser.roleCode === 'supplier';
    this.setData({
      ...buildInitialState(),
      loading: true,
      allowed,
      roleLabel: getRoleLabel(currentUser.roleCode),
      runtimeLabel: getRuntimeModeLabel(runtimeMode),
      sourceText: this.data.sourceText,
      sourceDetailText: this.data.sourceDetailText,
      selectedOrderId: this.data.selectedOrderId,
    });

    if (!allowed) {
      this.setData({ loading: false });
      return;
    }

    try {
      const response = await listSupplierPurchaseOrders('', { limit: 20 });
      const orders = this._decorateOrders(response.data.items || []);
      const selectedOrderId = this._resolveSelectedOrderId(orders, this.data.selectedOrderId);
      this.setData({
        loading: false,
        summaryCards: buildSupplierSummaryCards(response.data.items || []),
        orders,
        selectedOrderId,
        emptyText: response.data.total ? '请选择一条采购订单查看详情。' : '当前暂无可查看的采购订单。',
      });
      if (selectedOrderId > 0) {
        await this._loadDetail(selectedOrderId);
      }
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '供应商采购进度加载失败，请稍后重试',
      });
    }
  },

  onOpenOrder(event) {
    const orderId = Number(event.currentTarget.dataset.orderId || 0);
    if (!orderId || orderId === this.data.selectedOrderId) {
      return;
    }
    this.setData({ selectedOrderId: orderId });
    this._loadDetail(orderId);
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

  async _loadDetail(orderId) {
    this.setData({ detailLoading: true, detailErrorMessage: '' });
    try {
      const response = await getSupplierPurchaseOrderDetail(orderId);
      this.setData({
        detailLoading: false,
        selectedOrder: this._decorateDetail(response.data),
      });
    } catch (error) {
      this.setData({
        detailLoading: false,
        selectedOrder: null,
        detailErrorMessage: error.message || '采购订单详情加载失败，请稍后重试',
      });
    }
  },

  _resolveSelectedOrderId(orders, selectedOrderId) {
    const matched = (orders || []).find((item) => item.id === Number(selectedOrderId));
    if (matched) {
      return matched.id;
    }
    return orders.length ? orders[0].id : 0;
  },

  _decorateOrders(items) {
    return (items || []).map((item) => ({
      ...item,
      statusClass: resolvePurchaseOrderStatusClass(item.status),
      qtyOrderedText: formatQty(item.qty_ordered),
      payableAmountText: formatMoney(item.payable_amount),
      createdAtText: formatDateTime(item.created_at),
      selected: Number(item.id) === Number(this.data.selectedOrderId),
    }));
  },

  _decorateDetail(item) {
    if (!item) {
      return null;
    }
    return {
      ...item,
      statusClass: resolvePurchaseOrderStatusClass(item.status),
      qtyOrderedText: formatQty(item.qty_ordered),
      payableAmountText: formatMoney(item.payable_amount),
      createdAtText: formatDateTime(item.created_at),
      preparationHints: buildSupplierPreparationHints(item),
    };
  },

  _redirectToLogin() {
    this.setData({
      ...buildInitialState(),
      loading: false,
      runtimeLabel: getRuntimeModeLabel(getRuntimeMode()),
    });
    wx.reLaunch({ url: '/pages/login/index' });
  },
});
