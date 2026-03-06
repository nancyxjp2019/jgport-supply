const test = require('node:test');
const assert = require('node:assert/strict');

process.env.TZ = 'Asia/Shanghai';

const { formatDateTime, formatMoney, formatQty } = require('../utils/format');

test('金额格式化保留两位并加千分位', () => {
  assert.equal(formatMoney('650025'), '650,025.00');
});

test('数量格式化保留三位并加千分位', () => {
  assert.equal(formatQty('1260.5'), '1,260.500');
});

test('时间格式化输出中文项目约定格式', () => {
  assert.equal(formatDateTime('2026-03-06T16:20:00+08:00'), '2026-03-06 16:20');
});
