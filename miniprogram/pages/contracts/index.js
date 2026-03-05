const { listPurchaseContracts, listSalesContracts } = require('../../utils/api');
const { formatDate, formatMoney, formatNumber, normalizeDateInput } = require('../../utils/format');
const { toContractStatusText } = require('../../utils/status');
const {
  DEFAULT_TIME_FILTER,
  FIXED_TIME_FILTER_OPTIONS,
  resolveFixedTimeFilterRange,
} = require('../../utils/time-filter');

const TAB_OPTIONS = {
  sales: { label: '销售合同' },
  purchase: { label: '采购合同' },
};
const ACTIVE_CONTRACT_STATUSES = ['EFFECTIVE', 'PARTIALLY_EXECUTED'];
const MAX_VISIBLE_CONTRACTS = 10;

function getTabLabel(role, tab) {
  if (role === 'CUSTOMER' && tab === 'sales') {
    return '合同';
  }
  return (TAB_OPTIONS[tab] && TAB_OPTIONS[tab].label) || tab;
}

function getHeroSubtitle(role) {
  if (role === 'CUSTOMER') {
    return '合同列表已切换到 V5 合同域，展示你的合同摘要和执行情况。';
  }
  return '合同列表已切换到 V5 合同域，展示销售合同和采购合同的执行情况。';
}

function buildAvailableTabs(role) {
  if (role === 'CUSTOMER') {
    return ['sales'];
  }
  if (role === 'SUPPLIER') {
    return ['purchase'];
  }
  return ['sales', 'purchase'];
}

function getContractDateSortValue(item) {
  const rawValue = item && item.contract_date ? normalizeDateInput(item.contract_date) : '';
  const timestamp = rawValue ? new Date(rawValue).getTime() : 0;
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function buildVisibleContracts(items) {
  return (items || [])
    .filter((item) => ACTIVE_CONTRACT_STATUSES.includes(String(item.status || '')))
    .sort((left, right) => getContractDateSortValue(right) - getContractDateSortValue(left))
    .slice(0, MAX_VISIBLE_CONTRACTS);
}

function isContractInTimeRange(contractDate, timeRange) {
  if (!timeRange || timeRange.value === 'ALL') {
    return true;
  }
  const normalizedDate = formatDate(contractDate);
  if (!normalizedDate) {
    return false;
  }
  return normalizedDate >= timeRange.fromDate && normalizedDate <= timeRange.toDate;
}

Page({
  data: {
    role: '',
    currentTab: 'sales',
    tabs: [],
    items: [],
    heroSubtitle: '合同列表已切换到 V5 合同域，展示销售合同和采购合同的执行情况。',
    displayRuleText: '当前仅展示执行中的合同，按合同日期从近到远排列，最多显示 10 条。其他状态合同暂不展示。',
    emptyText: '当前暂无执行中的合同',
    currentTimeFilter: DEFAULT_TIME_FILTER,
    timeFilterOptions: FIXED_TIME_FILTER_OPTIONS,
  },

  onLoad(options) {
    if (options.tab) {
      this.setData({ currentTab: String(options.tab) === 'purchase' ? 'purchase' : 'sales' });
    }
  },

  onShow() {
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '');
    const tabs = buildAvailableTabs(role);
    const currentTab = tabs.includes(this.data.currentTab) ? this.data.currentTab : tabs[0];
    this.setData({
      role,
      tabs: tabs.map((item) => ({ code: item, label: getTabLabel(role, item) })),
      currentTab,
      heroSubtitle: getHeroSubtitle(role),
    });
    this.loadData();
  },

  async loadData() {
    try {
      const timeRange = resolveFixedTimeFilterRange(this.data.currentTimeFilter);
      const res = this.data.currentTab === 'purchase'
        ? await listPurchaseContracts({ page_size: 100 })
        : await listSalesContracts({ page_size: 100 });
      const items = buildVisibleContracts((res.data || []).filter((item) => isContractInTimeRange(item.contract_date, timeRange))).map((item) => ({
        ...item,
        status_text: toContractStatusText(item.status),
        contract_date_text: formatDate(item.contract_date),
        qty_text: formatNumber(item.effective_contract_qty, 4),
        executed_text: formatNumber(item.executed_qty, 4),
        pending_text: formatNumber(item.pending_execution_qty, 4),
        amount_text: formatMoney(item.deposit_amount),
      }));
      this.setData({ items });
    } catch (error) {
      wx.showToast({ title: error.message || '加载合同失败', icon: 'none' });
    }
  },

  onSwitchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab || tab === this.data.currentTab) {
      return;
    }
    this.setData({ currentTab: tab });
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
});
