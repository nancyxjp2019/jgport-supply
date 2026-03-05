const { listSalesOrders } = require('../../../utils/api');
const { formatDate, formatMoney, formatNumber } = require('../../../utils/format');
const { toSalesOrderStatusText } = require('../../../utils/status');
const {
  DEFAULT_TIME_FILTER,
  FIXED_TIME_FILTER_OPTIONS,
  resolveFixedTimeFilterRange,
} = require('../../../utils/time-filter');

const STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '待运营', value: 'SUBMITTED' },
  { label: '待财务', value: 'OPERATOR_APPROVED' },
  { label: '采购执行中', value: 'CUSTOMER_PAYMENT_CONFIRMED' },
  { label: '待出库', value: 'READY_FOR_OUTBOUND' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '已驳回', value: 'REJECTED' },
  { label: '异常关闭', value: 'ABNORMAL_CLOSED' },
];
const FINANCE_WORKBENCH_PENDING_STATUS = 'OPERATOR_APPROVED';

function getRoleDefaultPendingStatus(role) {
  if (role === 'OPERATOR') {
    return 'SUBMITTED';
  }
  if (role === 'FINANCE') {
    return 'OPERATOR_APPROVED';
  }
  return '';
}

function buildInitialFilters(role, options = {}) {
  const pendingOnly = options.pendingOnly === '1';
  let currentStatus = String(options.status || '');
  const centerMode = options.centerMode === '1';
  const currentTimeFilter = resolveFixedTimeFilterRange(String(options.timeFilter || DEFAULT_TIME_FILTER).toUpperCase()).value;
  const financeWorkbench = role === 'FINANCE' && options.financeWorkbench === '1';
  if (financeWorkbench) {
    return {
      centerMode,
      pendingOnly: true,
      currentStatus: FINANCE_WORKBENCH_PENDING_STATUS,
      financeWorkbench: true,
      currentTimeFilter,
    };
  }
  if (pendingOnly && !currentStatus) {
    currentStatus = getRoleDefaultPendingStatus(role);
  }
  return {
    centerMode,
    pendingOnly,
    currentStatus,
    financeWorkbench: false,
    currentTimeFilter,
  };
}

function buildCustomerCopy(role, centerMode) {
  if (role === 'CUSTOMER' || (role === 'OPERATOR' && centerMode)) {
    return {
      navTitle: '订单',
      heroTitle: '订单',
      heroSubtitle: role === 'CUSTOMER'
        ? '当前列表展示你的订单状态、履约进度和合同关联情况。'
        : '当前列表展示销售订单状态、履约进度和合同关联情况。',
      emptyText: '当前没有符合条件的订单',
    };
  }
  return {
    navTitle: '销售订单',
    heroTitle: '销售订单',
    heroSubtitle: '当前列表已切到 V5 销售订单模型，状态和动作均以双订单流程为准。',
    emptyText: '当前没有符合条件的销售订单',
  };
}

Page({
  data: {
    role: '',
    loading: false,
    pendingOnly: false,
    currentStatus: '',
    financeWorkbench: false,
    currentTimeFilter: DEFAULT_TIME_FILTER,
    timeFilterOptions: FIXED_TIME_FILTER_OPTIONS,
    statusOptions: STATUS_OPTIONS,
    items: [],
    centerMode: false,
    navTitle: '销售订单',
    heroTitle: '销售订单',
    heroSubtitle: '当前列表已切到 V5 销售订单模型，状态和动作均以双订单流程为准。',
    emptyText: '当前没有符合条件的销售订单',
  },

  onLoad(options) {
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '');
    const filters = buildInitialFilters(role, options);
    const copy = buildCustomerCopy(role, filters.centerMode);
    wx.setNavigationBarTitle({ title: copy.navTitle });
    this.setData({
      role,
      ...filters,
      ...copy,
    });
  },

  onShow() {
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '');
    const copy = buildCustomerCopy(role, this.data.centerMode);
    const nextState = {
      role,
      ...copy,
    };
    if (this.data.financeWorkbench) {
      nextState.pendingOnly = true;
      nextState.currentStatus = FINANCE_WORKBENCH_PENDING_STATUS;
    } else if (this.data.pendingOnly && !this.data.currentStatus) {
      nextState.currentStatus = getRoleDefaultPendingStatus(role);
    }
    this.setData(nextState);
    wx.setNavigationBarTitle({ title: copy.navTitle });
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const pendingOnly = this.data.financeWorkbench ? true : this.data.pendingOnly;
      const currentStatus = this.data.financeWorkbench ? FINANCE_WORKBENCH_PENDING_STATUS : this.data.currentStatus;
      const timeRange = resolveFixedTimeFilterRange(this.data.currentTimeFilter);
      const query = {
        pending_only: pendingOnly,
        status: currentStatus,
        page_size: 50,
      };
      if (timeRange.value !== 'ALL') {
        query.from_date = timeRange.fromDate;
        query.to_date = timeRange.toDate;
      }
      const res = await listSalesOrders(query);
      const items = (res.data || []).map((item) => ({
        ...item,
        status_text: toSalesOrderStatusText(item.status),
        order_date_text: formatDate(item.order_date),
        qty_text: formatNumber(item.qty_ton, 4),
        amount_text: formatMoney(item.amount_tax_included),
      }));
      this.setData({ items });
    } catch (error) {
      wx.showToast({ title: error.message || '加载失败', icon: 'none' });
    }
    this.setData({ loading: false });
  },

  onTapStatus(e) {
    if (this.data.financeWorkbench) {
      return;
    }
    const value = e.currentTarget.dataset.value || '';
    this.setData({ currentStatus: value });
    this.loadData();
  },

  onPickTimeFilter(e) {
    const value = String(e.currentTarget.dataset.value || DEFAULT_TIME_FILTER);
    if (value === this.data.currentTimeFilter) {
      return;
    }
    this.setData({ currentTimeFilter: value });
    this.loadData();
  },

  onTogglePending() {
    if (this.data.financeWorkbench) {
      return;
    }
    const nextPendingOnly = !this.data.pendingOnly;
    const defaultPendingStatus = getRoleDefaultPendingStatus(this.data.role);
    let currentStatus = this.data.currentStatus;
    if (nextPendingOnly && !currentStatus) {
      currentStatus = defaultPendingStatus;
    }
    if (!nextPendingOnly && currentStatus === defaultPendingStatus) {
      currentStatus = '';
    }
    this.setData({
      pendingOnly: nextPendingOnly,
      currentStatus,
    });
    this.loadData();
  },

  onOpenDetail(e) {
    const orderId = e.currentTarget.dataset.id;
    if (!orderId) {
      return;
    }
    wx.navigateTo({ url: `/pages/sales-orders/detail/index?id=${orderId}` });
  },

  onCreate() {
    wx.navigateTo({ url: '/pages/sales-orders/create/index' });
  },
});
