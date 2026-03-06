const STORAGE_MESSAGE_READ_KEY = 'mini_message_read_keys';
const { buildExecPageUrl, buildOrderPageUrl, buildReportPageUrl } = require('./navigation');

function normalizeRoleCode(roleCode) {
  return String(roleCode || '').trim().toLowerCase();
}

function buildMessages(options) {
  const roleCode = normalizeRoleCode(options && options.roleCode);
  if (roleCode === 'customer') {
    return buildCustomerMessages(options && options.orders);
  }
  if (['operations', 'finance', 'admin'].includes(roleCode)) {
    return buildOperatorMessages(options && options.overview);
  }
  if (roleCode === 'warehouse') {
    return buildWarehouseMessages();
  }
  if (roleCode === 'supplier') {
    return buildSupplierMessages();
  }
  return buildUnknownMessages();
}

function buildCustomerMessages(orders) {
  return (Array.isArray(orders) ? orders : [])
    .map((item) => buildCustomerMessage(item))
    .filter(Boolean)
    .sort(sortByTimeDesc);
}

function buildCustomerMessage(order) {
  const status = String(order.status || '').trim();
  const time = order.submitted_at || order.created_at || '';
  if (status === '驳回') {
    return {
      key: `customer-rejected-${order.id}-${status}-${time}`,
      level: 'danger',
      title: `订单 ${order.order_no} 已驳回`,
      summary: order.finance_comment || order.ops_comment || '请根据驳回意见补充后重新提交。',
      time,
      actionLabel: '去修改',
      actionUrl: buildOrderPageUrl({
        tab: 'query',
        editOrderId: order.id,
        source: 'message',
        sourceDetail: `已从消息定位到订单 ${order.order_no} 的编辑入口。`,
      }),
    };
  }
  if (status === '草稿') {
    return {
      key: `customer-draft-${order.id}-${status}-${time}`,
      level: 'info',
      title: `订单 ${order.order_no} 仍为草稿`,
      summary: '当前订单尚未提交审批，可继续补充后提交。',
      time,
      actionLabel: '继续处理',
      actionUrl: buildOrderPageUrl({
        tab: 'query',
        editOrderId: order.id,
        source: 'message',
        sourceDetail: `已从消息定位到订单 ${order.order_no} 的草稿编辑入口。`,
      }),
    };
  }
  if (status === '待运营审批') {
    return {
      key: `customer-pending-ops-${order.id}-${status}-${time}`,
      level: 'warning',
      title: `订单 ${order.order_no} 待运营审批`,
      summary: '订单已提交，正在等待运营处理。',
      time,
      actionLabel: '查看订单',
      actionUrl: buildOrderPageUrl({
        tab: 'query',
        status,
        source: 'message',
        sourceDetail: `已从消息定位到订单 ${order.order_no} 的审批进度。`,
      }),
    };
  }
  if (status === '待财务审批') {
    return {
      key: `customer-pending-finance-${order.id}-${status}-${time}`,
      level: 'warning',
      title: `订单 ${order.order_no} 待财务审批`,
      summary: '运营已通过，当前等待财务继续处理。',
      time,
      actionLabel: '查看订单',
      actionUrl: buildOrderPageUrl({
        tab: 'query',
        status,
        source: 'message',
        sourceDetail: `已从消息定位到订单 ${order.order_no} 的审批进度。`,
      }),
    };
  }
  if (status === '已衍生采购订单') {
    return {
      key: `customer-derived-${order.id}-${status}-${time}`,
      level: 'success',
      title: `订单 ${order.order_no} 已进入执行`,
      summary: '订单已衍生采购订单，可继续跟踪执行进度。',
      time,
      actionLabel: '查看订单',
      actionUrl: buildOrderPageUrl({
        tab: 'query',
        status,
        source: 'message',
        sourceDetail: `已从消息定位到订单 ${order.order_no} 的执行进度。`,
      }),
    };
  }
  return null;
}

function buildOperatorMessages(overview) {
  const source = overview || {};
  const snapshotTime = String(source.snapshot_time || '').trim() || 'none';
  const items = [
    {
      key: `operator-pending-${source.pending_supplement_count || 0}-${snapshotTime}`,
      level: 'warning',
      value: Number(source.pending_supplement_count || 0),
      focusKey: 'pending',
      title: '存在待补录金额单据',
      summary: '请优先补录金额或凭证，避免后续闭环受阻。',
    },
    {
      key: `operator-failed-${source.validation_failed_count || 0}-${snapshotTime}`,
      level: 'danger',
      value: Number(source.validation_failed_count || 0),
      focusKey: 'failed',
      title: '存在校验失败阻断',
      summary: '当前有单据因阈值或流程校验失败，需尽快处理。',
    },
    {
      key: `operator-qtydone-${source.qty_done_not_closed_count || 0}-${snapshotTime}`,
      level: 'info',
      value: Number(source.qty_done_not_closed_count || 0),
      focusKey: 'qtydone',
      title: '存在数量履约完成未关闭合同',
      summary: '请核对金额闭环并完成合同关闭。',
    },
  ]
    .filter((item) => item.value > 0)
    .map((item) => ({
      key: item.key,
      level: item.level,
      title: item.title,
      summary: `${item.summary} 当前 ${item.value} 项。`,
      time: source.snapshot_time || '',
      actionLabel: '查看快报',
      actionUrl: buildReportPageUrl({
        focusAbnormal: item.focusKey,
        source: 'message',
        sourceDetail: `已从消息定位到${item.title}。`,
      }),
    }));
  if (items.length) {
    return items;
  }
  return [
    {
      key: `operator-clean-${source.snapshot_time || 'none'}`,
      level: 'success',
      title: '当前暂无异常消息',
      summary: '待补录金额、校验失败和未关闭合同当前均为 0。',
      time: source.snapshot_time || '',
      actionLabel: '查看快报',
      actionUrl: buildReportPageUrl({
        source: 'message',
        sourceDetail: '已从消息进入经营快报总览。',
      }),
    },
  ];
}

function buildWarehouseMessages() {
  return [
    {
      key: 'warehouse-system-entry',
      level: 'info',
      title: '正常回执入口已开放',
      summary: '可通过正常回执路径提交仓库回执并直接生效。',
      time: '',
      actionLabel: '去处理',
      actionUrl: buildExecPageUrl({
        mode: 'system',
        source: 'message',
        sourceDetail: '已从消息定位到正常回执入口。',
      }),
    },
    {
      key: 'warehouse-manual-entry',
      level: 'warning',
      title: '手工补录入口已开放',
      summary: '异常场景下可使用手工补录，但仍需绑定订单、合同与油品。',
      time: '',
      actionLabel: '去处理',
      actionUrl: buildExecPageUrl({
        mode: 'manual',
        source: 'message',
        sourceDetail: '已从消息定位到手工补录入口。',
      }),
    },
  ];
}

function buildSupplierMessages() {
  return [
    {
      key: 'supplier-boundary',
      level: 'info',
      title: '供应商消息首批仅做边界提示',
      summary: '当前版本尚未开放供应商真实业务消息，后续在采购执行模块接入。',
      time: '',
      actionLabel: '',
      actionUrl: '',
    },
  ];
}

function buildUnknownMessages() {
  return [
    {
      key: 'unknown-role',
      level: 'info',
      title: '当前身份暂无可用消息',
      summary: '请切换到已开放的业务角色后重试。',
      time: '',
      actionLabel: '',
      actionUrl: '',
    },
  ];
}

function decorateMessages(messages, readKeys) {
  const readSet = new Set(Array.isArray(readKeys) ? readKeys : []);
  return (Array.isArray(messages) ? messages : []).map((item) => ({
    ...item,
    read: readSet.has(item.key),
    statusText: readSet.has(item.key) ? '已读' : '未读',
    levelClass: resolveLevelClass(item.level),
  }));
}

function filterMessages(messages, activeTab) {
  const items = Array.isArray(messages) ? messages : [];
  if (activeTab === 'unread') {
    return items.filter((item) => !item.read);
  }
  if (activeTab === 'read') {
    return items.filter((item) => item.read);
  }
  return items;
}

function countUnread(messages) {
  return (Array.isArray(messages) ? messages : []).filter((item) => !item.read).length;
}

function getStoredReadKeys(storage) {
  const adapter = resolveStorageAdapter(storage);
  const raw = adapter.get(STORAGE_MESSAGE_READ_KEY);
  return Array.isArray(raw) ? raw : [];
}

function markMessageRead(storage, key) {
  if (!key) {
    return getStoredReadKeys(storage);
  }
  return markMessagesRead(storage, [key]);
}

function markMessagesRead(storage, keys) {
  const next = Array.from(new Set([...getStoredReadKeys(storage), ...(Array.isArray(keys) ? keys : [])]));
  const adapter = resolveStorageAdapter(storage);
  adapter.set(STORAGE_MESSAGE_READ_KEY, next);
  return next;
}

function resolveStorageAdapter(storage) {
  if (storage && typeof storage.get === 'function' && typeof storage.set === 'function') {
    return storage;
  }
  return {
    get(key) {
      if (typeof wx === 'undefined' || typeof wx.getStorageSync !== 'function') {
        return [];
      }
      return wx.getStorageSync(key);
    },
    set(key, value) {
      if (typeof wx !== 'undefined' && typeof wx.setStorageSync === 'function') {
        wx.setStorageSync(key, value);
      }
    },
  };
}

function resolveLevelClass(level) {
  if (level === 'danger') {
    return 'msg-level--danger';
  }
  if (level === 'warning') {
    return 'msg-level--warning';
  }
  if (level === 'success') {
    return 'msg-level--success';
  }
  return 'msg-level--info';
}

function sortByTimeDesc(left, right) {
  return String(right.time || '').localeCompare(String(left.time || ''));
}

module.exports = {
  buildMessages,
  countUnread,
  decorateMessages,
  filterMessages,
  getStoredReadKeys,
  markMessageRead,
  markMessagesRead,
};
