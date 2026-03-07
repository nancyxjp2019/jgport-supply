const DEMO_CONTRACTS = [
  {
    id: 901,
    contract_no: 'DEMO-SALES-202603-001',
    customer_id: 'AUTO-TEST-CUSTOMER-COMPANY',
    items: [
      { oil_product_id: 'OIL-92', qty_signed: '120.000', unit_price: '6500.25' },
      { oil_product_id: 'OIL-95', qty_signed: '80.000', unit_price: '6720.80' },
    ],
  },
  {
    id: 902,
    contract_no: 'DEMO-SALES-202603-002',
    customer_id: 'AUTO-TEST-CUSTOMER-COMPANY',
    items: [
      { oil_product_id: 'OIL-0', qty_signed: '60.000', unit_price: '5988.60' },
    ],
  },
];

const INITIAL_ORDERS = [
  {
    id: 1001,
    order_no: 'SO-DEMO-001',
    sales_contract_id: 901,
    sales_contract_no: 'DEMO-SALES-202603-001',
    oil_product_id: 'OIL-92',
    qty_ordered: '20.000',
    unit_price: '6500.25',
    status: '待运营审批',
    submit_comment: '请尽快安排审批',
    ops_comment: null,
    finance_comment: null,
    purchase_order_id: null,
    submitted_at: '2026-03-06T09:10:00+08:00',
    created_at: '2026-03-06T09:00:00+08:00',
  },
  {
    id: 1002,
    order_no: 'SO-DEMO-002',
    sales_contract_id: 902,
    sales_contract_no: 'DEMO-SALES-202603-002',
    oil_product_id: 'OIL-0',
    qty_ordered: '12.500',
    unit_price: '5988.60',
    status: '驳回',
    submit_comment: '补充收货信息后重提',
    ops_comment: '数量口径需核实',
    finance_comment: null,
    purchase_order_id: null,
    submitted_at: '2026-03-05T16:30:00+08:00',
    created_at: '2026-03-05T16:00:00+08:00',
  },
];

let demoOrders = INITIAL_ORDERS.map((item) => ({ ...item }));
let demoOrderIdSeed = 2000;

const DEMO_PURCHASE_ORDERS = [
  {
    id: 3001,
    order_no: 'PO-DEMO-001',
    purchase_contract_id: 801,
    source_sales_order_id: 1001,
    source_sales_order_no: 'SO-DEMO-001',
    supplier_id: 'AUTO-TEST-SUPPLIER-COMPANY',
    oil_product_id: 'OIL-92',
    qty_ordered: '20.000',
    payable_amount: '11800.12',
    status: '待供应商确认',
    zero_pay_exception_flag: false,
    created_at: '2026-03-06T10:00:00+08:00',
    message: '演示模式：供应商采购订单详情查询成功',
  },
  {
    id: 3002,
    order_no: 'PO-DEMO-002',
    purchase_contract_id: 802,
    source_sales_order_id: 1002,
    source_sales_order_no: 'SO-DEMO-002',
    supplier_id: 'AUTO-TEST-SUPPLIER-COMPANY',
    oil_product_id: 'OIL-0',
    qty_ordered: '12.500',
    payable_amount: '0.00',
    status: '可继续执行',
    zero_pay_exception_flag: true,
    created_at: '2026-03-05T15:30:00+08:00',
    message: '演示模式：供应商采购订单详情查询成功',
  },
];

function listDemoAvailableSalesContracts() {
  return DEMO_CONTRACTS.map((contract) => ({
    ...contract,
    items: contract.items.map((item) => ({ ...item })),
  }));
}

function listDemoSalesOrders(status) {
  const normalized = String(status || '').trim();
  const items = normalized ? demoOrders.filter((item) => item.status === normalized) : demoOrders;
  return items.map((item) => ({ ...item }));
}

function createDemoSalesOrder(payload) {
  demoOrderIdSeed += 1;
  const contract = DEMO_CONTRACTS.find((item) => item.id === Number(payload.sales_contract_id));
  const order = {
    id: demoOrderIdSeed,
    order_no: `SO-DEMO-${demoOrderIdSeed}`,
    sales_contract_id: Number(payload.sales_contract_id),
    sales_contract_no: contract ? contract.contract_no : `DEMO-SALES-${payload.sales_contract_id}`,
    oil_product_id: payload.oil_product_id,
    qty_ordered: payload.qty,
    unit_price: payload.unit_price,
    status: '草稿',
    submit_comment: null,
    ops_comment: null,
    finance_comment: null,
    purchase_order_id: null,
    submitted_at: null,
    created_at: new Date().toISOString(),
    message: '演示模式：订单草稿已创建',
  };
  demoOrders = [order, ...demoOrders];
  return { ...order };
}

function updateDemoSalesOrder(orderId, payload) {
  const target = demoOrders.find((item) => item.id === Number(orderId));
  if (!target) {
    throw new Error('当前订单不存在，请刷新后重试');
  }
  if (!['草稿', '驳回'].includes(target.status)) {
    throw new Error('当前订单状态不允许在演示模式下修改');
  }
  target.sales_contract_id = Number(payload.sales_contract_id);
  const contract = DEMO_CONTRACTS.find((item) => item.id === Number(payload.sales_contract_id));
  target.sales_contract_no = contract ? contract.contract_no : `DEMO-SALES-${payload.sales_contract_id}`;
  target.oil_product_id = payload.oil_product_id;
  target.qty_ordered = payload.qty;
  target.unit_price = payload.unit_price;
  target.status = target.status === '驳回' ? '草稿' : target.status;
  target.message = target.status === '草稿' ? '演示模式：订单草稿已更新' : '演示模式：订单已更新';
  return { ...target };
}

function submitDemoSalesOrder(orderId, comment) {
  const target = demoOrders.find((item) => item.id === Number(orderId));
  if (!target) {
    throw new Error('当前订单不存在，请刷新后重试');
  }
  if (target.status !== '草稿') {
    throw new Error('当前订单状态不允许提交审批');
  }
  target.status = '待运营审批';
  target.submit_comment = comment;
  target.submitted_at = new Date().toISOString();
  target.message = '演示模式：订单已提交运营审批';
  return { ...target };
}

function listDemoSupplierPurchaseOrders() {
  return DEMO_PURCHASE_ORDERS.map((item) => ({ ...item }));
}

function getDemoSupplierPurchaseOrderDetail(orderId) {
  const target = DEMO_PURCHASE_ORDERS.find((item) => item.id === Number(orderId));
  if (!target) {
    throw new Error('当前采购订单不存在，请刷新后重试');
  }
  return { ...target };
}

module.exports = {
  createDemoSalesOrder,
  getDemoSupplierPurchaseOrderDetail,
  listDemoAvailableSalesContracts,
  listDemoSalesOrders,
  listDemoSupplierPurchaseOrders,
  submitDemoSalesOrder,
  updateDemoSalesOrder,
};
