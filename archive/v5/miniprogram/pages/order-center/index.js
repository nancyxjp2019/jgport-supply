function buildEntries(role) {
  if (role === 'FINANCE') {
    return [
      { title: '销售订单', desc: '查看销售订单审核与履约进度', url: '/pages/sales-orders/list/index' },
      { title: '采购订单', desc: '查看采购订单提交与执行进度', url: '/pages/purchase-orders/list/index' },
    ];
  }
  return [
    { title: '销售订单', desc: '查看销售订单状态与履约进度', url: '/pages/sales-orders/list/index?centerMode=1' },
  ];
}

function buildSubtitle(role) {
  if (role === 'FINANCE') {
    return '当前按销售订单、采购订单分入口查询，分别承接客户收款审核和采购执行协同。';
  }
  return '当前按订单类型查看执行进度与状态。';
}

Page({
  data: {
    role: '',
    heroSubtitle: '当前按订单类型查看执行进度与状态。',
    entries: [],
  },

  onShow() {
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '').trim();
    this.setData({
      role,
      heroSubtitle: buildSubtitle(role),
      entries: buildEntries(role),
    });
  },

  onOpenEntry(e) {
    const url = e.currentTarget.dataset.url;
    if (!url) {
      return;
    }
    wx.navigateTo({ url });
  },
});
