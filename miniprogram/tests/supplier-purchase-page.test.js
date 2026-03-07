const test = require('node:test');
const assert = require('node:assert/strict');

let pageConfig = null;

global.Page = (config) => {
  pageConfig = config;
};

global.wx = {
  reLaunch() {},
  showToast() {},
};

require('../pages/supplier-purchase/index');

test('采购详情页装饰器会挂载付款校验结果视图', () => {
  const detail = pageConfig._decorateDetail(
    {
      id: 3003,
      order_no: 'PO-DEMO-003',
      purchase_contract_id: 803,
      source_sales_order_id: 1003,
      source_sales_order_no: 'SO-DEMO-003',
      supplier_id: 'AUTO-TEST-SUPPLIER-COMPANY',
      oil_product_id: 'OIL-95',
      qty_ordered: '8.000',
      payable_amount: '9200.00',
      status: '待付款校验',
      zero_pay_exception_flag: false,
      created_at: '2026-03-05T18:00:00+08:00',
    },
    [],
  );
  assert.equal(detail.paymentValidationView.statusText, '待付款校验中');
  assert.match(detail.paymentValidationView.hintText, /付款校验完成/);
});
