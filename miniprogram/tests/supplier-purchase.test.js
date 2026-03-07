const test = require('node:test');
const assert = require('node:assert/strict');

const {
  buildSupplierAttachmentItems,
  buildSupplierPreparationHints,
  getSupplierAttachmentTagOptions,
  resolveSupplierAttachmentTagLabel,
} = require('../utils/supplier-purchase');

test('供应商附件标签可输出中文选项与标签名', () => {
  const options = getSupplierAttachmentTagOptions();
  assert.equal(options.length, 2);
  assert.equal(resolveSupplierAttachmentTagLabel('SUPPLIER_STAMPED_DOC'), '盖章发货指令单');
  assert.equal(resolveSupplierAttachmentTagLabel('SUPPLIER_DELIVERY_RECEIPT'), '供应商回单');
});

test('供应商附件摘要会补齐中文标签', () => {
  const items = buildSupplierAttachmentItems([
    { id: 1, biz_tag: 'SUPPLIER_STAMPED_DOC', file_path: 'CODEX-TEST-/a.pdf' },
  ]);
  assert.equal(items[0].bizTagLabel, '盖章发货指令单');
});

test('发货准备提示会反映附件首批已开放与已登记数量', () => {
  const hints = buildSupplierPreparationHints({
    source_sales_order_no: 'SO-001',
    status: '可继续执行',
    zero_pay_exception_flag: false,
    attachments: [{ id: 1 }, { id: 2 }],
  });
  assert.match(hints[2], /首批附件回传/);
  assert.match(hints[3], /当前已登记附件 2 份/);
});
