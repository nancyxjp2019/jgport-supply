const { listPurchaseOrders } = require('../../../utils/api');
const { formatDate, formatNumber } = require('../../../utils/format');
const { toPurchaseOrderStatusText } = require('../../../utils/status');
const {
  DEFAULT_TIME_FILTER,
  FIXED_TIME_FILTER_OPTIONS,
  resolveFixedTimeFilterRange,
} = require('../../../utils/time-filter');

const STATUS_OPTIONS = [
  { label: '全部', value: '' },
  { label: '待提交', value: 'PENDING_SUBMIT' },
  { label: '待供应商', value: 'SUPPLIER_REVIEW_PENDING' },
  { label: '待仓库', value: 'WAREHOUSE_PENDING' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '异常关闭', value: 'ABNORMAL_CLOSED' },
];
const FINANCE_WORKBENCH_PENDING_STATUS = 'PENDING_SUBMIT';
const WAREHOUSE_WORKBENCH_PENDING_STATUS = 'WAREHOUSE_PENDING';

function buildInitialFilters(role, options = {}) {
  const financeWorkbench = role === 'FINANCE' && options.financeWorkbench === '1';
  const warehouseWorkbench = role === 'WAREHOUSE' && options.warehouseWorkbench === '1';
  const currentTimeFilter = resolveFixedTimeFilterRange(String(options.timeFilter || DEFAULT_TIME_FILTER).toUpperCase()).value;
  if (financeWorkbench) {
    return {
      pendingOnly: true,
      currentStatus: FINANCE_WORKBENCH_PENDING_STATUS,
      financeWorkbench: true,
      warehouseWorkbench: false,
      currentTimeFilter,
    };
  }
  if (warehouseWorkbench) {
    return {
      pendingOnly: true,
      currentStatus: WAREHOUSE_WORKBENCH_PENDING_STATUS,
      financeWorkbench: false,
      warehouseWorkbench: true,
      currentTimeFilter,
    };
  }
  return {
    pendingOnly: options.pendingOnly === '1',
    currentStatus: String(options.status || ''),
    financeWorkbench: false,
    warehouseWorkbench: false,
    currentTimeFilter,
  };
}

Page({
  data: {
    role: '',
    pendingOnly: false,
    currentStatus: '',
    financeWorkbench: false,
    warehouseWorkbench: false,
    currentTimeFilter: DEFAULT_TIME_FILTER,
    timeFilterOptions: FIXED_TIME_FILTER_OPTIONS,
    statusOptions: STATUS_OPTIONS,
    items: [],
  },

  onLoad(options) {
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '');
    const filters = buildInitialFilters(role, options);
    this.setData({ role, ...filters });
  },

  onShow() {
    if (this.data.financeWorkbench) {
      this.setData({
        pendingOnly: true,
        currentStatus: FINANCE_WORKBENCH_PENDING_STATUS,
      });
    } else if (this.data.warehouseWorkbench) {
      this.setData({
        pendingOnly: true,
        currentStatus: WAREHOUSE_WORKBENCH_PENDING_STATUS,
      });
    }
    this.loadData();
  },

  async loadData() {
    try {
      const forcePendingOnly = this.data.financeWorkbench || this.data.warehouseWorkbench;
      const pendingOnly = forcePendingOnly ? true : this.data.pendingOnly;
      const currentStatus = this.data.financeWorkbench
        ? FINANCE_WORKBENCH_PENDING_STATUS
        : this.data.warehouseWorkbench
          ? WAREHOUSE_WORKBENCH_PENDING_STATUS
          : this.data.currentStatus;
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
      const res = await listPurchaseOrders(query);
      const items = (res.data || []).map((item) => ({
        ...item,
        status_text: toPurchaseOrderStatusText(item.status),
        created_at_text: formatDate(item.created_at),
        qty_text: formatNumber(item.qty_ton, 4),
      }));
      this.setData({ items });
    } catch (error) {
      wx.showToast({ title: error.message || '加载失败', icon: 'none' });
    }
  },

  onTapStatus(e) {
    if (this.data.financeWorkbench || this.data.warehouseWorkbench) {
      return;
    }
    this.setData({ currentStatus: e.currentTarget.dataset.value || '' });
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
    if (this.data.financeWorkbench || this.data.warehouseWorkbench) {
      return;
    }
    this.setData({ pendingOnly: !this.data.pendingOnly });
    this.loadData();
  },

  onOpenDetail(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) {
      return;
    }
    wx.navigateTo({ url: `/pages/purchase-orders/detail/index?id=${id}` });
  },
});
