const test = require('node:test');
const assert = require('node:assert/strict');

const {
  confirmDemoSupplierPurchaseOrderDelivery,
  createDemoSupplierPurchaseOrderAttachment,
  getDemoSupplierPurchaseOrderDetail,
  listDemoSupplierPurchaseOrderAttachments,
} = require('../mocks/order');

test('演示模式供应商采购详情不暴露内部任务字段', () => {
  const detail = getDemoSupplierPurchaseOrderDetail(3001);
  assert.equal(detail.id, 3001);
  assert.ok(!Object.prototype.hasOwnProperty.call(detail, 'downstream_tasks'));
  assert.ok(!Object.prototype.hasOwnProperty.call(detail, 'idempotency_key'));
});

test('演示模式供应商附件可登记并加入摘要列表', () => {
  const beforeItems = listDemoSupplierPurchaseOrderAttachments(3002);
  const created = createDemoSupplierPurchaseOrderAttachment(3002, {
    biz_tag: 'SUPPLIER_DELIVERY_RECEIPT',
    file_path: 'CODEX-TEST-/demo-supplier-delivery-receipt-001.pdf',
  });
  const afterItems = listDemoSupplierPurchaseOrderAttachments(3002);
  assert.equal(created.biz_tag, 'SUPPLIER_DELIVERY_RECEIPT');
  assert.equal(afterItems.length, beforeItems.length + 1);
  assert.equal(afterItems[0].file_path, 'CODEX-TEST-/demo-supplier-delivery-receipt-001.pdf');
});

test('演示模式供应商可提交单笔发货确认', () => {
  const confirmed = confirmDemoSupplierPurchaseOrderDelivery(3001, 'CODEX-TEST-演示确认');
  assert.equal(confirmed.status, '供应商已确认');
  assert.equal(confirmed.supplier_confirm_comment, 'CODEX-TEST-演示确认');
  assert.ok(confirmed.supplier_confirmed_at);
});
