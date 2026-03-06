const test = require('node:test');
const assert = require('node:assert/strict');

const {
  buildAbnormalItems,
  canViewLightReport,
  getRoleLabel,
  isOverviewEmpty,
  resolveOverviewStatusText,
} = require('../utils/light-report');

const demoOverview = {
  pending_supplement_count: 1,
  validation_failed_count: 2,
  qty_done_not_closed_count: 3,
  actual_receipt_today: '10.00',
  actual_payment_today: '20.00',
  inbound_qty_today: '1.000',
  outbound_qty_today: '2.000',
  abnormal_count: 6,
};

test('仅运营侧角色可查看轻量报表', () => {
  assert.equal(canViewLightReport('operations'), true);
  assert.equal(canViewLightReport('finance'), true);
  assert.equal(canViewLightReport('admin'), true);
  assert.equal(canViewLightReport('customer'), false);
});

test('角色标签输出中文', () => {
  assert.equal(getRoleLabel('warehouse'), '仓库');
  assert.equal(getRoleLabel('finance'), '财务');
});

test('异常分桶固定为三类且数值正确', () => {
  const items = buildAbnormalItems(demoOverview);
  assert.equal(items.length, 3);
  assert.deepEqual(
    items.map((item) => item.value),
    [1, 2, 3],
  );
});

test('SLA 延迟时展示更新中提示', () => {
  assert.equal(resolveOverviewStatusText('延迟'), '数据更新中，请稍后再试');
  assert.equal(resolveOverviewStatusText('正常'), '数据已更新');
});

test('空报表判定基于四项汇总与异常数全部为0', () => {
  assert.equal(
    isOverviewEmpty({
      actual_receipt_today: '0.00',
      actual_payment_today: '0.00',
      inbound_qty_today: '0.000',
      outbound_qty_today: '0.000',
      abnormal_count: 0,
    }),
    true,
  );
  assert.equal(isOverviewEmpty(demoOverview), false);
});
