const { clearSession, fetchMe } = require('../../utils/auth');
const { getInventorySummary, listPurchaseOrders, listSalesOrders } = require('../../utils/api');
const { formatNumber } = require('../../utils/format');

const ROLE_LABEL_MAP = {
  CUSTOMER: '客户',
  OPERATOR: '运营',
  FINANCE: '财务',
  SUPPLIER: '供应商',
  WAREHOUSE: '仓库',
  ADMIN: '业务管理员',
};

function getRoleDefaultSalesPendingStatus(role) {
  if (role === 'OPERATOR') {
    return 'SUBMITTED';
  }
  if (role === 'FINANCE') {
    return 'OPERATOR_APPROVED';
  }
  return '';
}

function getRoleDefaultPurchasePendingStatus(role) {
  if (role === 'FINANCE') {
    return 'PENDING_SUBMIT';
  }
  if (role === 'WAREHOUSE') {
    return 'WAREHOUSE_PENDING';
  }
  return '';
}

function buildEntries(role) {
  if (role === 'CUSTOMER') {
    return [
      { title: '新建订单', desc: '客户建单与运输资料提交', url: '/pages/sales-orders/create/index', tone: 'warm' },
      { title: '订单中心', desc: '查看自己的订单与履约进度', url: '/pages/sales-orders/list/index' },
      { title: '合同中心', desc: '查看可执行合同摘要与执行情况', url: '/pages/contracts/index?tab=sales' },
      { title: '报表中心', desc: '生成和下载销售侧轻量报表', url: '/pages/reports/index?tab=sales_orders' },
    ];
  }
  if (role === 'OPERATOR') {
    return [
      { title: '待审订单', desc: '处理待运营审核订单', url: '/pages/sales-orders/list/index?pendingOnly=1' },
      { title: '订单中心', desc: '查看销售订单与履约进度', url: '/pages/sales-orders/list/index?centerMode=1' },
      { title: '合同中心', desc: '统一查看销售合同与采购合同摘要', url: '/pages/contracts/index' },
      { title: '报表中心', desc: '查看销售、采购、库存轻量报表', url: '/pages/reports/index' },
    ];
  }
  if (role === 'FINANCE') {
    return [
      { title: '待审核销售订单', desc: '确认客户收款并生成采购订单', url: '/pages/sales-orders/list/index?pendingOnly=1&status=OPERATOR_APPROVED&financeWorkbench=1' },
      { title: '待处理采购订单', desc: '提交待处理采购订单并上传付款凭证', url: '/pages/purchase-orders/list/index?pendingOnly=1&status=PENDING_SUBMIT&financeWorkbench=1' },
      { title: '订单中心', desc: '查看销售订单与采购订单进度', url: '/pages/order-center/index' },
      { title: '合同中心', desc: '查看销售合同与采购合同摘要', url: '/pages/contracts/index' },
      { title: '报表中心', desc: '生成合同、订单、库存轻量报表', url: '/pages/reports/index' },
    ];
  }
  if (role === 'SUPPLIER') {
    return [
      { title: '待审订单', desc: '查看发货指令单并上传盖章单据', url: '/pages/purchase-orders/list/index?pendingOnly=1' },
      { title: '采购订单', desc: '查看本公司采购订单', url: '/pages/purchase-orders/list/index' },
      { title: '采购合同', desc: '查看本公司采购合同摘要', url: '/pages/contracts/index?tab=purchase' },
      { title: '采购报表', desc: '生成本公司采购轻量报表', url: '/pages/reports/index?tab=purchase_orders' },
    ];
  }
  if (role === 'WAREHOUSE') {
    return [
      { title: '待出库订单', desc: '仓库确认出库并上传出库单', url: '/pages/purchase-orders/list/index?pendingOnly=1&status=WAREHOUSE_PENDING&warehouseWorkbench=1' },
      { title: '仓库台账', desc: '查看本仓出入库台账与下载', url: '/pages/reports/index?tab=warehouse_ledger' },
    ];
  }
  if (role === 'ADMIN') {
    return [
      { title: '销售订单', desc: '查看全量销售订单与终止操作', url: '/pages/sales-orders/list/index' },
      { title: '采购订单', desc: '查看全量采购订单与异常关闭', url: '/pages/purchase-orders/list/index' },
      { title: '合同中心', desc: '查看销售合同与采购合同摘要', url: '/pages/contracts/index' },
      { title: '报表中心', desc: '查看全量 V5 轻量报表', url: '/pages/reports/index' },
    ];
  }
  return [];
}

Page({
  data: {
    user: null,
    roleLabel: '',
    pendingCount: 0,
    entries: [],
    inventorySummary: null,
  },

  async onShow() {
    const app = getApp();
    if (!app.globalData.token) {
      wx.reLaunch({ url: '/pages/login/index' });
      return;
    }
    try {
      const res = await fetchMe();
      app.globalData.user = res.data;
      wx.setStorageSync('user', res.data);
    } catch (_error) {}

    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '').trim();
    this.setData({
      user,
      roleLabel: ROLE_LABEL_MAP[role] || role || '业务角色',
      entries: buildEntries(role),
    });
    await this.loadPendingCount(role);
    await this.loadInventorySummary(role);
  },

  async loadPendingCount(role) {
    try {
      let count = 0;
      if (['CUSTOMER', 'OPERATOR', 'FINANCE', 'ADMIN'].includes(role)) {
        const salesRes = await listSalesOrders({
          pending_only: true,
          status: getRoleDefaultSalesPendingStatus(role),
          page_size: 100,
        });
        count += (salesRes.data || []).length;
      }
      if (['FINANCE', 'SUPPLIER', 'WAREHOUSE', 'ADMIN'].includes(role)) {
        const purchaseRes = await listPurchaseOrders({
          pending_only: true,
          status: getRoleDefaultPurchasePendingStatus(role),
          page_size: 100,
        });
        count += (purchaseRes.data || []).length;
      }
      this.setData({ pendingCount: count });
    } catch (_error) {
      this.setData({ pendingCount: 0 });
    }
  },

  async loadInventorySummary(role) {
    if (!['FINANCE', 'OPERATOR'].includes(role)) {
      this.setData({ inventorySummary: null });
      return;
    }
    try {
      const res = await getInventorySummary();
      const payload = res.data || {};
      this.setData({
        inventorySummary: {
          warehouse_items: (payload.warehouse_items || []).map((item) => ({
            warehouse_id: item.warehouse_id,
            warehouse_name: item.warehouse_name,
            low_stock_item_count: Number(item.low_stock_item_count || 0),
            product_item_count: Array.isArray(item.product_items) ? item.product_items.length : 0,
            product_items: (item.product_items || []).map((productItem) => ({
              product_id: productItem.product_id,
              product_name: productItem.product_name,
              on_hand_qty_text: formatNumber(productItem.on_hand_qty_ton, 4),
              reserved_qty_text: formatNumber(productItem.reserved_qty_ton, 4),
              available_qty_text: formatNumber(productItem.available_qty_ton, 4),
            })),
          })),
        },
      });
    } catch (_error) {
      this.setData({ inventorySummary: null });
    }
  },

  onOpenEntry(e) {
    const url = e.currentTarget.dataset.url;
    if (!url) {
      return;
    }
    wx.navigateTo({ url });
  },

  onLogout() {
    clearSession();
    wx.reLaunch({ url: '/pages/login/index' });
  },
});
