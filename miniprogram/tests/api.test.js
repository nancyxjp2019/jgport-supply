const test = require('node:test');
const assert = require('node:assert/strict');

const { getDemoSupplierPurchaseOrderDetail } = require('../mocks/order');

test('演示模式供应商采购详情不暴露内部任务字段', () => {
  const detail = getDemoSupplierPurchaseOrderDetail(3001);
  assert.equal(detail.id, 3001);
  assert.ok(!Object.prototype.hasOwnProperty.call(detail, 'downstream_tasks'));
  assert.ok(!Object.prototype.hasOwnProperty.call(detail, 'idempotency_key'));
});
