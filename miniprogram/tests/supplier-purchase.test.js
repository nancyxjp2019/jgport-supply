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

test('待供应商确认与供应商已确认会输出对应中文提示', () => {
  const pendingHints = buildSupplierPreparationHints({
    source_sales_order_no: 'SO-002',
    status: '待供应商确认',
    zero_pay_exception_flag: false,
    attachments: [],
  });
  const confirmedHints = buildSupplierPreparationHints({
    source_sales_order_no: 'SO-003',
    status: '供应商已确认',
    zero_pay_exception_flag: true,
    attachments: [],
  });
  assert.match(pendingHints[3], /建议先完成附件留痕/);
  assert.match(confirmedHints[3], /等待付款校验/);
});
