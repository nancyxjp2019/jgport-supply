const { generateReport, listReports } = require('../../utils/api');
const { openRemoteFile } = require('../../utils/file');
const { formatDateTime } = require('../../utils/format');
const {
  DEFAULT_TIME_FILTER,
  FIXED_TIME_FILTER_OPTIONS,
  getFixedTimeFilterLabel,
  resolveFixedTimeFilterRange,
} = require('../../utils/time-filter');

const REPORT_TABS = {
  CUSTOMER: ['SALES_ORDERS', 'SALES_CONTRACTS'],
  OPERATOR: ['SALES_ORDERS', 'PURCHASE_ORDERS', 'SALES_CONTRACTS', 'PURCHASE_CONTRACTS', 'INVENTORY_MOVEMENTS'],
  FINANCE: ['SALES_ORDERS', 'PURCHASE_ORDERS', 'SALES_CONTRACTS', 'PURCHASE_CONTRACTS', 'INVENTORY_MOVEMENTS', 'WAREHOUSE_LEDGER'],
  SUPPLIER: ['PURCHASE_ORDERS', 'PURCHASE_CONTRACTS'],
  WAREHOUSE: ['WAREHOUSE_LEDGER'],
  ADMIN: ['SALES_ORDERS', 'PURCHASE_ORDERS', 'SALES_CONTRACTS', 'PURCHASE_CONTRACTS', 'INVENTORY_MOVEMENTS', 'WAREHOUSE_LEDGER'],
};

const REPORT_LABEL_MAP = {
  SALES_ORDERS: '销售订单报表',
  PURCHASE_ORDERS: '采购订单报表',
  SALES_CONTRACTS: '销售合同报表',
  PURCHASE_CONTRACTS: '采购合同报表',
  INVENTORY_MOVEMENTS: '库存变动报表',
  WAREHOUSE_LEDGER: '仓库台账',
};

function getReportLabel(role, reportCode) {
  if (role === 'CUSTOMER' && reportCode === 'SALES_ORDERS') {
    return '订单报表';
  }
  if (role === 'CUSTOMER' && reportCode === 'SALES_CONTRACTS') {
    return '合同报表';
  }
  return REPORT_LABEL_MAP[reportCode] || reportCode;
}

function getHeroSubtitle(role) {
  if (role === 'CUSTOMER') {
    return '按当前所选报表类型和时间范围生成，并在下方查看本公司报表列表。';
  }
  return '当前报表中心已切换到 V5 分域报表模型，按角色自动裁剪可见报表类型和字段。';
}

Page({
  data: {
    role: '',
    tabs: [],
    tabItems: [],
    currentTab: 'SALES_ORDERS',
    currentTimeFilter: DEFAULT_TIME_FILTER,
    currentTimeFilterLabel: '本周',
    heroSubtitle: '',
    items: [],
    loading: false,
    generating: false,
    generatingTab: '',
    timeFilterOptions: FIXED_TIME_FILTER_OPTIONS,
  },

  onLoad(options) {
    if (options.tab) {
      const tabMap = {
        sales_orders: 'SALES_ORDERS',
        purchase_orders: 'PURCHASE_ORDERS',
        warehouse_ledger: 'WAREHOUSE_LEDGER',
      };
      this.setData({ currentTab: tabMap[String(options.tab || '').toLowerCase()] || 'SALES_ORDERS' });
    }
  },

  onShow() {
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '');
    const tabs = REPORT_TABS[role] || [];
    const currentTab = tabs.includes(this.data.currentTab) ? this.data.currentTab : tabs[0];
    this.setData({
      role,
      tabs,
      tabItems: tabs.map((item) => ({ code: item, label: getReportLabel(role, item) })),
      currentTab,
      currentTimeFilterLabel: getFixedTimeFilterLabel(this.data.currentTimeFilter),
      heroSubtitle: getHeroSubtitle(role),
    });
    this.loadData();
  },

  buildTimeFilterQuery() {
    const timeRange = resolveFixedTimeFilterRange(this.data.currentTimeFilter);
    if (timeRange.value === 'ALL') {
      return { days: 0 };
    }
    return {
      from_date: timeRange.fromDate,
      to_date: timeRange.toDate,
    };
  },

  async loadData() {
    if (!this.data.currentTab) {
      return;
    }
    this.setData({ loading: true });
    try {
      const timeFilterQuery = this.buildTimeFilterQuery();
      const res = await listReports(this.data.currentTab, {
        ...timeFilterQuery,
        limit: 5,
        offset: 0,
      });
      const items = ((res.data && res.data.items) || []).map((item) => ({
        ...item,
        created_at_text: formatDateTime(item.created_at),
      }));
      this.setData({ items });
    } catch (error) {
      wx.showToast({ title: error.message || '加载报表失败', icon: 'none' });
    }
    this.setData({ loading: false });
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
    this.setData({
      currentTimeFilter: value,
      currentTimeFilterLabel: getFixedTimeFilterLabel(value),
    });
    this.loadData();
  },

  buildGeneratePayload() {
    const timeRange = resolveFixedTimeFilterRange(this.data.currentTimeFilter);
    if (timeRange.value === 'ALL') {
      return {
        days: 0,
        from_date: null,
        to_date: null,
      };
    }
    return {
      days: null,
      from_date: timeRange.fromDate,
      to_date: timeRange.toDate,
    };
  },

  async onGenerate() {
    if (!this.data.currentTab || this.data.generating) {
      return;
    }
    this.setData({ generating: true, generatingTab: this.data.currentTab });
    try {
      await generateReport(this.data.currentTab, this.buildGeneratePayload());
      wx.showToast({ title: '报表生成成功', icon: 'success' });
      await this.loadData();
    } catch (error) {
      wx.showToast({ title: error.message || '报表生成失败', icon: 'none' });
    }
    this.setData({ generating: false, generatingTab: '' });
  },

  async onOpenReport(e) {
    const url = e.currentTarget.dataset.url;
    const fileName = e.currentTarget.dataset.name;
    if (!url) {
      wx.showToast({ title: '暂无下载地址', icon: 'none' });
      return;
    }
    try {
      await openRemoteFile(url, { fileName });
    } catch (error) {
      wx.showToast({ title: error.message || '打开失败', icon: 'none' });
    }
  },
});
