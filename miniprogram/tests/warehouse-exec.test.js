const test = require('node:test');
const assert = require('node:assert/strict');

const {
  buildDemoExecResponse,
  buildExecSummary,
  buildManualOutboundPayload,
  buildWarehouseConfirmPayload,
} = require('../utils/warehouse-exec');

test('正常回执表单校验会阻断空字段', () => {
  const result = buildWarehouseConfirmPayload({
    contractId: '',
    salesOrderId: '10',
    sourceTicketNo: '',
    actualQty: '0',
    warehouseId: '',
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.contractId, '销售合同ID不能为空');
  assert.equal(result.errors.sourceTicketNo, '仓库回执号不能为空');
  assert.equal(result.errors.actualQty, '实际出库数量必须大于0');
});

test('手工补录表单校验通过后保留原始业务字段', () => {
  const result = buildManualOutboundPayload({
    contractId: '11',
    salesOrderId: '22',
    oilProductId: 'OIL-92',
    manualRefNo: 'MANUAL-001',
    actualQty: '35.500',
    reason: '现场补录',
    warehouseId: 'WH-001',
  });
  assert.equal(result.isValid, true);
  assert.equal(result.payload.manual_ref_no, 'MANUAL-001');
  assert.equal(result.payload.actual_qty, '35.500');
});

test('演示模式执行结果固定返回已过账中文状态', () => {
  const response = buildDemoExecResponse('system', {
    contract_id: '1',
    sales_order_id: '2',
    source_ticket_no: 'T-001',
    actual_qty: '10.000',
    warehouse_id: 'WH-001',
  });
  assert.equal(response.status, '已过账');
  assert.equal(response.source_type, 'SYSTEM');
  assert.match(response.doc_no, /^OUT-DEMO-/);
});

test('执行结果摘要输出中文字段标签', () => {
  const summary = buildExecSummary(
    {
      doc_no: 'OUT-001',
      source_ticket_no: 'SRC-001',
      actual_qty: '20.000',
      status: '已过账',
    },
    'system',
  );
  assert.deepEqual(summary[0], { label: '出库单号', value: 'OUT-001' });
  assert.deepEqual(summary[1], { label: '仓库回执号', value: 'SRC-001' });
});
