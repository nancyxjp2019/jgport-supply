const { getRuntimeMode, getRuntimeModeLabel } = require('../../config/env');
const { getAccessProfile, getLightReportOverview, listSalesOrders } = require('../../utils/api');
const { formatDateTime } = require('../../utils/format');
const { getRoleLabel } = require('../../utils/light-report');
const { getAccessToken, initializeSession, logoutSession, updateAccessProfile } = require('../../utils/session');
const {
  buildMessages,
  countUnread,
  decorateMessages,
  filterMessages,
  getStoredReadKeys,
  markMessageRead,
  markMessagesRead,
} = require('../../utils/message');

function buildInitialState() {
  return {
    loading: true,
    errorMessage: '',
    roleLabel: '',
    runtimeLabel: '演示模式',
    activeTab: 'all',
    summaryCards: [],
    messages: [],
    filteredMessages: [],
    emptyTitle: '当前暂无消息',
    emptyText: '系统正在等待新的业务提醒。',
    helperText: '首批消息中心基于当前已开放业务链聚合生成。',
    unreadCount: 0,
  };
}

function buildSummaryCards(messages) {
  const items = Array.isArray(messages) ? messages : [];
  const unreadCount = countUnread(items);
  const readCount = items.length - unreadCount;
  const warningCount = items.filter((item) => ['danger', 'warning'].includes(item.level)).length;
  return [
    {
      key: 'all',
      label: '全部消息',
      value: String(items.length),
      desc: '当前身份可见的首批消息聚合。',
      className: 'todo-summary-card--normal',
    },
    {
      key: 'unread',
      label: '未读消息',
      value: String(unreadCount),
      desc: '未处理或未阅读的消息提醒。',
      className: unreadCount > 0 ? 'todo-summary-card--warning' : 'todo-summary-card--normal',
    },
    {
      key: 'focus',
      label: '重点关注',
      value: String(warningCount),
      desc: '高优先级或需立即跟进的消息数量。',
      className: warningCount > 0 ? 'todo-summary-card--danger' : 'todo-summary-card--normal',
    },
    {
      key: 'read',
      label: '已读消息',
      value: String(readCount),
      desc: '已完成阅读的消息数量。',
      className: 'todo-summary-card--success',
    },
  ];
}

function buildEmptyState(activeTab) {
  if (activeTab === 'unread') {
    return {
      emptyTitle: '当前没有未读消息',
      emptyText: '已读完本轮消息，可下拉刷新等待新的业务提醒。',
    };
  }
  if (activeTab === 'read') {
    return {
      emptyTitle: '当前没有已读消息',
      emptyText: '你还没有将任何消息标记为已读。',
    };
  }
  return {
    emptyTitle: '当前暂无消息',
    emptyText: '系统正在等待新的业务提醒。',
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

    this.setData({
      ...buildInitialState(),
      loading: true,
      roleLabel: getRoleLabel(currentUser.roleCode),
      runtimeLabel: getRuntimeModeLabel(runtimeMode),
      activeTab: this.data.activeTab || 'all',
    });

    try {
      let messages = [];
      if (currentUser.roleCode === 'customer') {
        const response = await listSalesOrders('', { limit: 50 });
        messages = buildMessages({ roleCode: currentUser.roleCode, orders: response.data.items || [] });
      } else if (['operations', 'finance', 'admin'].includes(currentUser.roleCode)) {
        const response = await getLightReportOverview();
        messages = buildMessages({ roleCode: currentUser.roleCode, overview: response.data });
      } else {
        messages = buildMessages({ roleCode: currentUser.roleCode });
      }
      this._applyMessages(messages, this.data.activeTab || 'all');
    } catch (error) {
      if (Number(error.statusCode || 0) === 401) {
        logoutSession();
        wx.showToast({ title: error.message || '登录状态已失效，请重新登录', icon: 'none' });
        this._redirectToLogin();
        return;
      }
      this.setData({
        loading: false,
        errorMessage: error.message || '消息中心加载失败，请稍后重试',
      });
    }
    wx.stopPullDownRefresh();
  },

  onSwitchTab(event) {
    const activeTab = String(event.currentTarget.dataset.tab || 'all');
    const state = buildEmptyState(activeTab);
    this.setData({
      activeTab,
      filteredMessages: filterMessages(this.data.messages, activeTab),
      emptyTitle: state.emptyTitle,
      emptyText: state.emptyText,
    });
  },

  onOpenMessage(event) {
    const key = String(event.currentTarget.dataset.key || '').trim();
    const url = String(event.currentTarget.dataset.url || '').trim();
    if (key) {
      this._markAsRead(key);
    }
    if (!url) {
      wx.showToast({ title: '当前消息暂无可跳转页面', icon: 'none' });
      return;
    }
    wx.navigateTo({ url });
  },

  onMarkRead(event) {
    const key = String(event.currentTarget.dataset.key || '').trim();
    if (!key) {
      return;
    }
    this._markAsRead(key, true);
  },

  onMarkAllRead() {
    const unreadKeys = this.data.messages.filter((item) => !item.read).map((item) => item.key);
    if (!unreadKeys.length) {
      wx.showToast({ title: '当前没有未读消息', icon: 'none' });
      return;
    }
    const readKeys = markMessagesRead(null, unreadKeys);
    this._refreshReadState(readKeys, this.data.activeTab);
    wx.showToast({ title: '已全部标记为已读', icon: 'success' });
  },

  onSwitchRole() {
    wx.reLaunch({ url: '/pages/login/index' });
  },

  onLogout() {
    logoutSession();
    wx.reLaunch({ url: '/pages/login/index' });
  },

  _applyMessages(messages, activeTab) {
    const readKeys = getStoredReadKeys();
    const decorated = decorateMessages(
      (Array.isArray(messages) ? messages : []).map((item) => ({
        ...item,
        timeText: item.time ? formatDateTime(item.time) : '等待触发',
      })),
      readKeys,
    );
    const state = buildEmptyState(activeTab);
    this.setData({
      loading: false,
      errorMessage: '',
      summaryCards: buildSummaryCards(decorated),
      messages: decorated,
      filteredMessages: filterMessages(decorated, activeTab),
      unreadCount: countUnread(decorated),
      emptyTitle: state.emptyTitle,
      emptyText: state.emptyText,
    });
  },

  _markAsRead(key, showToast) {
    const readKeys = markMessageRead(null, key);
    this._refreshReadState(readKeys, this.data.activeTab);
    if (showToast) {
      wx.showToast({ title: '已标记为已读', icon: 'success' });
    }
  },

  _refreshReadState(readKeys, activeTab) {
    const nextMessages = decorateMessages(this.data.messages, readKeys);
    const state = buildEmptyState(activeTab);
    this.setData({
      messages: nextMessages,
      filteredMessages: filterMessages(nextMessages, activeTab),
      summaryCards: buildSummaryCards(nextMessages),
      unreadCount: countUnread(nextMessages),
      emptyTitle: state.emptyTitle,
      emptyText: state.emptyText,
    });
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
