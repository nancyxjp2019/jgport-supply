const { getRuntimeMode, getRuntimeModeLabel } = require('../../config/env');
const { getAccessProfile, getLightReportOverview, listSalesOrders, listSupplierPurchaseOrders } = require('../../utils/api');
const { formatDateTime, formatMoney, formatQty } = require('../../utils/format');
const { getRoleLabel } = require('../../utils/light-report');
const { getAccessToken, initializeSession, logoutSession, updateAccessProfile } = require('../../utils/session');
const {
  buildCustomerSummaryCards,
  buildCustomerTodoItems,
  buildOperatorSummaryCards,
  buildOperatorTodoItems,
  buildSupplierSummaryCards,
  buildSupplierTodoItems,
  buildWarehouseQuickActions,
  buildWarehouseSummaryCards,
  resolveTodoMode,
} = require('../../utils/todo');

function buildInitialState() {
  return {
    loading: true,
    errorMessage: '',
    roleLabel: '',
    runtimeLabel: '演示模式',
    todoMode: 'unknown',
    summaryCards: [],
    todoItems: [],
    quickActions: [],
    emptyTitle: '当前暂无待办',
    emptyText: '系统正在等待新的业务动作。',
    helperText: '',
    snapshotTimeText: '',
  };
}

Page({
  data: buildInitialState(),

  onShow() {
    this.loadPage();
  },

  onPullDownRefresh() {
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
    const todoMode = resolveTodoMode(currentUser.roleCode);
    this.setData({
      ...buildInitialState(),
      loading: true,
      roleLabel,
      runtimeLabel: getRuntimeModeLabel(runtimeMode),
      todoMode,
    });

    try {
      if (todoMode === 'customer') {
        await this._loadCustomerTodo();
      } else if (todoMode === 'operator') {
        await this._loadOperatorTodo();
      } else if (todoMode === 'warehouse') {
        this._loadWarehouseTodo();
      } else if (todoMode === 'supplier') {
        await this._loadSupplierTodo();
      } else {
        this._loadUnknownTodo();
      }
    } catch (error) {
      if (Number(error.statusCode || 0) === 401) {
        logoutSession();
        wx.showToast({ title: error.message || '登录状态已失效，请重新登录', icon: 'none' });
        this._redirectToLogin();
        return;
      }
      this.setData({
        loading: false,
        errorMessage: error.message || '待办加载失败，请稍后重试',
      });
    }
    wx.stopPullDownRefresh();
  },

  async _loadCustomerTodo() {
    const response = await listSalesOrders('', { limit: 50 });
    const orders = response.data.items || [];
    const todoItems = buildCustomerTodoItems(orders).map((item) => ({
      ...item,
      qtyOrderedText: formatQty(item.qtyOrdered),
      createdAtText: formatDateTime(item.createdAt),
      submittedAtText: formatDateTime(item.submittedAt),
    }));
    this.setData({
      loading: false,
      summaryCards: buildCustomerSummaryCards(orders),
      todoItems,
      quickActions: [
        {
          key: 'message',
          title: '查看消息中心',
          desc: '统一查看订单提醒、异常消息和执行入口通知。',
          url: '/pages/msg/index',
          actionLabel: '去查看',
        },
        {
          key: 'create',
          title: '发起新订单',
          desc: '按合同和油品创建订单草稿，再提交审批。',
          url: '/pages/order/index?tab=create',
          actionLabel: '去发起',
        },
        {
          key: 'query',
          title: '查看全部订单',
          desc: '查询当前公司订单状态和审批进度。',
          url: '/pages/order/index?tab=query',
          actionLabel: '去查看',
        },
      ],
      emptyTitle: '当前暂无需要处理的订单',
      emptyText: '如需继续业务，可直接发起新订单。',
      helperText: '客户待办首批聚焦订单发起、补充和进度跟踪。',
    });
  },

  async _loadOperatorTodo() {
    const response = await getLightReportOverview();
    const overview = response.data;
    this.setData({
      loading: false,
      summaryCards: buildOperatorSummaryCards(overview),
      todoItems: buildOperatorTodoItems(overview),
      quickActions: [
        {
          key: 'message',
          title: '查看消息中心',
          desc: '统一查看异常提醒和首批状态通知。',
          url: '/pages/msg/index',
          actionLabel: '去查看',
        },
        {
          key: 'report',
          title: '查看经营快报',
          desc: '查看当日实收实付、出入库和异常摘要。',
          url: '/pages/report/index',
          actionLabel: '去查看',
        },
      ],
      emptyTitle: '当前暂无异常待办',
      emptyText: '异常摘要为 0 时，表示当前无待补录和校验失败阻断。',
      helperText: '小程序待办首批以异常摘要为主，详细处理动作仍在管理后台完成。',
      snapshotTimeText: formatDateTime(overview.snapshot_time),
    });
  },

  _loadWarehouseTodo() {
    this.setData({
      loading: false,
      summaryCards: buildWarehouseSummaryCards(),
      todoItems: [],
      quickActions: [
        ...buildWarehouseQuickActions(),
        {
          key: 'message',
          title: '查看消息中心',
          desc: '查看执行入口开放提醒与当前角色首批消息。',
          url: '/pages/msg/index',
          actionLabel: '去查看',
        },
      ],
      emptyTitle: '当前没有独立待办列表',
      emptyText: '仓库角色当前通过执行回执页处理现场业务。',
      helperText: '执行回执已开放正常回执和手工补录，同时可在消息中心查看首批提醒。',
    });
  },

  async _loadSupplierTodo() {
    const response = await listSupplierPurchaseOrders('', { limit: 20 });
    const purchaseOrders = response.data.items || [];
    const todoItems = buildSupplierTodoItems(purchaseOrders).map((item) => ({
      ...item,
      qtyOrderedText: formatQty(item.qtyOrdered),
      payableAmountText: formatMoney(item.payableAmount),
      createdAtText: formatDateTime(item.createdAt),
    }));
    this.setData({
      loading: false,
      summaryCards: buildSupplierSummaryCards(purchaseOrders),
      todoItems,
      quickActions: [
        {
          key: 'progress',
          title: '查看采购进度',
          desc: '查看当前供应商公司名下采购订单进度与发货准备信息。',
          url: '/pages/supplier-purchase/index',
          actionLabel: '去查看',
        },
        {
          key: 'message',
          title: '查看消息中心',
          desc: '查看采购进度提醒与入口定位消息。',
          url: '/pages/msg/index',
          actionLabel: '去查看',
        },
      ],
      emptyTitle: '当前暂无供应商采购订单',
      emptyText: '待财务审批生成采购订单后，这里会展示真实采购进度入口。',
      helperText: '供应商首批已开放采购进度查看、发货准备回看与附件入口预留。',
    });
  },

  _loadUnknownTodo() {
    this.setData({
      loading: false,
      summaryCards: [],
      todoItems: [],
      quickActions: [
        {
          key: 'message',
          title: '查看消息中心',
          desc: '查看当前身份是否存在系统边界提示。',
          url: '/pages/msg/index',
          actionLabel: '去查看',
        },
      ],
      emptyTitle: '当前身份暂无可用待办',
      emptyText: '请切换到已开放的业务角色后重试。',
      helperText: '若当前角色不正确，请先退出后重新登录。',
    });
  },

  onOpenAction(event) {
    const url = String(event.currentTarget.dataset.url || '').trim();
    if (!url) {
      return;
    }
    wx.navigateTo({ url });
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
      ...buildInitialState(),
      loading: false,
      runtimeLabel: getRuntimeModeLabel(getRuntimeMode()),
    });
    wx.stopPullDownRefresh();
    wx.reLaunch({ url: '/pages/login/index' });
  },
});
