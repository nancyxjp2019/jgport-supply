const test = require('node:test');
const assert = require('node:assert/strict');

const {
  buildMessages,
  countUnread,
  decorateMessages,
  filterMessages,
  getStoredReadKeys,
  markMessageRead,
  markMessagesRead,
} = require('../utils/message');

function createStorageAdapter() {
  const store = new Map();
  return {
    store,
    adapter: {
      get(key) {
        return store.get(key);
      },
      set(key, value) {
        store.set(key, value);
      },
    },
  };
}

test('客户消息会按时间倒序聚合草稿与驳回提醒', () => {
  const messages = buildMessages({
    roleCode: 'customer',
    orders: [
      {
        id: 1,
        order_no: 'SO-001',
        status: '草稿',
        created_at: '2026-03-05T08:00:00Z',
      },
      {
        id: 2,
        order_no: 'SO-002',
        status: '驳回',
        finance_comment: '请补充付款说明',
        created_at: '2026-03-06T09:00:00Z',
      },
    ],
  });
  assert.equal(messages.length, 2);
  assert.equal(messages[0].title, '订单 SO-002 已驳回');
  assert.equal(messages[0].actionLabel, '去修改');
  assert.match(messages[0].actionUrl, /source=message/);
  assert.match(messages[0].actionUrl, /editOrderId=2/);
  assert.equal(messages[1].title, '订单 SO-001 仍为草稿');
});

test('运营侧消息会根据异常计数生成重点提醒', () => {
  const messages = buildMessages({
    roleCode: 'finance',
    overview: {
      pending_supplement_count: 2,
      validation_failed_count: 1,
      qty_done_not_closed_count: 0,
      snapshot_time: '2026-03-06T10:00:00Z',
    },
  });
  assert.equal(messages.length, 2);
  assert.match(messages[0].actionUrl, /^\/pages\/report\/index\?/);
  assert.match(messages[0].actionUrl, /source=message/);
  assert.equal(messages[0].time, '2026-03-06T10:00:00Z');
  assert.match(messages[0].key, /2026-03-06T10:00:00Z/);
});

test('仓库消息会携带统一深链参数', () => {
  const messages = buildMessages({ roleCode: 'warehouse' });
  assert.equal(messages.length, 2);
  assert.match(messages[0].actionUrl, /\/pages\/exec\/index\?/);
  assert.match(messages[0].actionUrl, /source=message/);
  assert.match(messages[1].actionUrl, /mode=manual/);
});

test('供应商消息会基于真实采购订单生成入口', () => {
  const messages = buildMessages({
    roleCode: 'supplier',
    purchaseOrders: [
      {
        id: 301,
        order_no: 'PO-001',
        source_sales_order_no: 'SO-001',
        status: '待供应商确认',
        created_at: '2026-03-06T10:00:00Z',
      },
    ],
  });
  assert.equal(messages.length, 1);
  assert.match(messages[0].title, /PO-001/);
  assert.match(messages[0].actionUrl, /supplier-purchase/);
  assert.match(messages[0].actionUrl, /source=message/);
});

test('运营侧无异常时会返回清空提示消息', () => {
  const messages = buildMessages({
    roleCode: 'operations',
    overview: {
      pending_supplement_count: 0,
      validation_failed_count: 0,
      qty_done_not_closed_count: 0,
      snapshot_time: '2026-03-06T10:00:00Z',
    },
  });
  assert.equal(messages.length, 1);
  assert.equal(messages[0].title, '当前暂无异常消息');
  assert.equal(messages[0].level, 'success');
});

test('消息装饰、筛选与未读统计会根据已读键生效', () => {
  const decorated = decorateMessages(
    [
      { key: 'm1', level: 'warning', title: '消息1' },
      { key: 'm2', level: 'info', title: '消息2' },
    ],
    ['m2'],
  );
  assert.equal(countUnread(decorated), 1);
  assert.equal(filterMessages(decorated, 'unread').length, 1);
  assert.equal(filterMessages(decorated, 'read')[0].key, 'm2');
  assert.equal(decorated[0].levelClass, 'msg-level--warning');
});

test('标记已读会写入本地存储并去重', () => {
  const { adapter, store } = createStorageAdapter();
  assert.deepEqual(getStoredReadKeys(adapter), []);
  markMessageRead(adapter, 'm1');
  markMessagesRead(adapter, ['m1', 'm2']);
  assert.deepEqual(store.get('mini_message_read_keys'), ['m1', 'm2']);
});
