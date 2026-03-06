const test = require('node:test');
const assert = require('node:assert/strict');

const {
  adaptContractOptions,
  buildOrderDraftPayload,
  buildOrderEditorState,
  canEditOrder,
  getOrderStatusClass,
  getOrderStatusOptions,
  validateSubmitComment,
} = require('../utils/order');

test('可选销售合同会适配为 picker 数据结构', () => {
  const result = adaptContractOptions([
    {
      id: 1,
      contract_no: 'SC-001',
      customer_id: 'CUSTOMER-001',
      items: [{ oil_product_id: 'OIL-92', qty_signed: '100.000', unit_price: '6500.25' }],
    },
  ]);
  assert.equal(result[0].contractNo, 'SC-001');
  assert.equal(result[0].items[0].oilProductId, 'OIL-92');
});

test('订单草稿表单校验会阻断空合同和非法数量', () => {
  const result = buildOrderDraftPayload({
    salesContractId: '',
    oilProductId: '',
    qty: '0',
    unitPrice: '',
  });
  assert.equal(result.isValid, false);
  assert.equal(result.errors.salesContractId, '请选择合同');
  assert.equal(result.errors.qty, '下单数量必须大于0');
});

test('订单编辑态可根据订单回填表单', () => {
  const editorState = buildOrderEditorState(
    {
      id: 99,
      sales_contract_id: 1,
      oil_product_id: 'OIL-95',
      qty_ordered: '18.000',
      unit_price: '6720.80',
      submit_comment: '加急',
    },
    [
      {
        id: 1,
        contractNo: 'SC-001',
        items: [
          { oilProductId: 'OIL-92', unitPrice: '6500.25' },
          { oilProductId: 'OIL-95', unitPrice: '6720.80' },
        ],
      },
    ],
  );
  assert.equal(editorState.editingOrderId, 99);
  assert.equal(editorState.selectedOilIndex, 1);
  assert.equal(editorState.form.oilProductId, 'OIL-95');
});

test('草稿和驳回状态允许继续编辑', () => {
  assert.equal(canEditOrder('草稿'), true);
  assert.equal(canEditOrder('驳回'), true);
  assert.equal(canEditOrder('待运营审批'), false);
  assert.equal(getOrderStatusClass('驳回'), 'status-pill--rejected');
});

test('提交审批说明不能为空', () => {
  assert.equal(validateSubmitComment(''), '提交审批说明不能为空');
  assert.equal(validateSubmitComment('客户提交审批'), '');
  assert.equal(getOrderStatusOptions().length >= 5, true);
});
