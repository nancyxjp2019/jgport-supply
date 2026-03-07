const test = require('node:test');
const assert = require('node:assert/strict');

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
} = require('../utils/todo');

test('客户角色会被识别为客户待办模式', () => {
  assert.equal(resolveTodoMode('customer'), 'customer');
  assert.equal(resolveTodoMode('finance'), 'operator');
  assert.equal(resolveTodoMode('warehouse'), 'warehouse');
  assert.equal(resolveTodoMode('supplier'), 'supplier');
});

test('客户待办摘要会按草稿、审批中、驳回聚合', () => {
  const cards = buildCustomerSummaryCards([
    { status: '草稿' },
    { status: '待运营审批' },
    { status: '待财务审批' },
    { status: '驳回' },
  ]);
  assert.equal(cards[0].value, 1);
  assert.equal(cards[1].value, 2);
  assert.equal(cards[2].value, 1);
});

test('客户待办列表只保留需要处理的订单并按优先级排序', () => {
  const items = buildCustomerTodoItems([
    { id: 1, order_no: 'SO-1', sales_contract_no: 'C-1', status: '待财务审批', oil_product_id: '92', qty_ordered: '10', created_at: '2026-03-05T08:00:00Z' },
    { id: 2, order_no: 'SO-2', sales_contract_no: 'C-2', status: '驳回', oil_product_id: '95', qty_ordered: '8', created_at: '2026-03-06T08:00:00Z' },
    { id: 3, order_no: 'SO-3', sales_contract_no: 'C-3', status: '已衍生采购订单', oil_product_id: '0', qty_ordered: '5', created_at: '2026-03-06T07:00:00Z' },
  ]);
  assert.equal(items.length, 2);
  assert.equal(items[0].orderNo, 'SO-2');
  assert.equal(items[0].actionLabel, '继续处理');
  assert.equal(items[0].actionUrl, '/pages/order/index?tab=query&editOrderId=2');
  assert.equal(items[1].actionLabel, '查看进度');
});

test('运营侧待办摘要和列表来自异常计数', () => {
  const overview = {
    pending_supplement_count: 2,
    validation_failed_count: 1,
    qty_done_not_closed_count: 0,
  };
  const cards = buildOperatorSummaryCards(overview);
  const items = buildOperatorTodoItems(overview);
  assert.equal(cards[0].value, 2);
  assert.equal(cards[1].value, 1);
  assert.equal(items.length, 2);
});

test('仓库待办首批返回固定快捷入口', () => {
  const actions = buildWarehouseQuickActions();
  const cards = buildWarehouseSummaryCards();
  assert.equal(actions.length, 2);
  assert.equal(actions[0].url, '/pages/exec/index?mode=system');
  assert.equal(cards[0].value, '已开放');
});

test('供应商待办摘要与列表基于真实采购订单生成', () => {
  const purchaseOrders = [
    {
      id: 1,
      order_no: 'PO-1',
      source_sales_order_no: 'SO-1',
      status: '待供应商确认',
      oil_product_id: 'OIL-92',
      qty_ordered: '10.000',
      payable_amount: '8000.12',
      zero_pay_exception_flag: false,
      created_at: '2026-03-06T08:00:00Z',
    },
    {
      id: 2,
      order_no: 'PO-2',
      source_sales_order_no: 'SO-2',
      status: '供应商已确认',
      oil_product_id: 'OIL-95',
      qty_ordered: '8.000',
      payable_amount: '0.00',
      zero_pay_exception_flag: true,
      created_at: '2026-03-05T08:00:00Z',
    },
  ];
  const cards = buildSupplierSummaryCards(purchaseOrders);
  const items = buildSupplierTodoItems(purchaseOrders);
  assert.equal(cards[0].value, 1);
  assert.equal(cards[1].value, 1);
  assert.equal(cards[2].value, 1);
  assert.equal(cards[3].value, 0);
  assert.equal(items[0].orderNo, 'PO-1');
  assert.equal(items[0].status, '待供应商确认');
  assert.match(items[0].actionUrl, /supplier-purchase/);
});
