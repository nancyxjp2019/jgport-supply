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
    supplier_confirm_comment: null,
    supplier_confirmed_at: null,
    payment_validation_status: '未进入付款校验',
    payment_validation_hint: '当前需先完成发货确认，发货确认提交后才会进入后续付款校验结果回看阶段。',
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
    status: '供应商已确认',
    zero_pay_exception_flag: true,
    supplier_confirm_comment: 'AUTO-TEST-供应商已完成发货确认',
    supplier_confirmed_at: '2026-03-05T17:00:00+08:00',
    payment_validation_status: '等待付款校验结果',
    payment_validation_hint: '当前已完成发货确认，并命中零付款例外场景；需等待运营/财务按冻结规则完成付款校验放行，后续仍需关注补录。',
    created_at: '2026-03-05T15:30:00+08:00',
    message: '演示模式：供应商采购订单详情查询成功',
  },
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
    supplier_confirm_comment: 'AUTO-TEST-已提交发货确认，等待付款校验',
    supplier_confirmed_at: '2026-03-05T19:00:00+08:00',
    payment_validation_status: '待付款校验中',
    payment_validation_hint: '当前正在等待付款校验完成；供应商侧暂不开放付款确认、驳回或异常关闭动作。',
    created_at: '2026-03-05T18:00:00+08:00',
    message: '演示模式：供应商采购订单详情查询成功',
  },
  {
    id: 3004,
    order_no: 'PO-DEMO-004',
    purchase_contract_id: 804,
    source_sales_order_id: 1004,
    source_sales_order_no: 'SO-DEMO-004',
    supplier_id: 'AUTO-TEST-SUPPLIER-COMPANY',
    oil_product_id: 'OIL-98',
    qty_ordered: '15.000',
    payable_amount: '15600.00',
    status: '可继续执行',
    zero_pay_exception_flag: false,
    supplier_confirm_comment: 'AUTO-TEST-付款校验已完成，可继续执行',
    supplier_confirmed_at: '2026-03-04T10:00:00+08:00',
    payment_validation_status: '已通过付款校验',
    payment_validation_hint: '当前采购订单已完成付款校验，可继续跟踪仓储、发运与后续执行进度。',
    created_at: '2026-03-04T09:00:00+08:00',
    message: '演示模式：供应商采购订单详情查询成功',
  },
  {
    id: 3005,
    order_no: 'PO-DEMO-005',
    purchase_contract_id: 805,
    source_sales_order_id: 1005,
    source_sales_order_no: 'SO-DEMO-005',
    supplier_id: 'AUTO-TEST-SUPPLIER-COMPANY',
    oil_product_id: 'OIL-0',
    qty_ordered: '6.000',
    payable_amount: '0.00',
    status: '执行中',
    zero_pay_exception_flag: true,
    supplier_confirm_comment: 'AUTO-TEST-例外放行后进入执行中',
    supplier_confirmed_at: '2026-03-03T12:30:00+08:00',
    payment_validation_status: '已完成付款校验并进入执行中',
    payment_validation_hint: '当前订单已进入执行中，说明付款校验已完成或已按例外规则放行；后续仍需关注执行反馈与补录闭环。',
    created_at: '2026-03-03T11:00:00+08:00',
    message: '演示模式：供应商采购订单详情查询成功',
  },
];

let demoPurchaseOrderAttachments = {
  3001: [
    {
      id: 4001,
      owner_doc_type: 'purchase_order',
      owner_doc_id: 3001,
      biz_tag: 'SUPPLIER_STAMPED_DOC',
      file_path: 'CODEX-TEST-/demo-supplier-stamped-doc-001.pdf',
      created_at: '2026-03-06T12:00:00+08:00',
    },
  ],
  3002: [],
  3003: [],
  3004: [],
  3005: [],
};
let demoPurchaseAttachmentIdSeed = 5000;

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

function listDemoSupplierPurchaseOrderAttachments(orderId) {
  const order = DEMO_PURCHASE_ORDERS.find((item) => item.id === Number(orderId));
  if (!order) {
    throw new Error('当前采购订单不存在，请刷新后重试');
  }
  return (demoPurchaseOrderAttachments[order.id] || []).map((item) => ({ ...item }));
}

function createDemoSupplierPurchaseOrderAttachment(orderId, payload) {
  const order = DEMO_PURCHASE_ORDERS.find((item) => item.id === Number(orderId));
  if (!order) {
    throw new Error('当前采购订单不存在，请刷新后重试');
  }
  const bizTag = String((payload && payload.biz_tag) || '').trim().toUpperCase();
  const filePath = String((payload && payload.file_path) || '').trim();
  if (!['SUPPLIER_STAMPED_DOC', 'SUPPLIER_DELIVERY_RECEIPT'].includes(bizTag)) {
    throw new Error('当前附件业务标签不在首批开放范围内');
  }
  if (!filePath) {
    throw new Error('附件路径不能为空');
  }
  const currentItems = demoPurchaseOrderAttachments[order.id] || [];
  if (currentItems.some((item) => item.biz_tag === bizTag && item.file_path === filePath)) {
    throw new Error('当前附件已存在，请勿重复上传');
  }
  demoPurchaseAttachmentIdSeed += 1;
  const attachment = {
    id: demoPurchaseAttachmentIdSeed,
    owner_doc_type: 'purchase_order',
    owner_doc_id: order.id,
    biz_tag: bizTag,
    file_path: filePath,
    created_at: new Date().toISOString(),
  };
  demoPurchaseOrderAttachments[order.id] = [attachment].concat(currentItems);
  return { ...attachment };
}

function confirmDemoSupplierPurchaseOrderDelivery(orderId, comment) {
  const order = DEMO_PURCHASE_ORDERS.find((item) => item.id === Number(orderId));
  if (!order) {
    throw new Error('当前采购订单不存在，请刷新后重试');
  }
  if (order.status !== '待供应商确认') {
    throw new Error('当前采购订单状态不允许提交发货确认');
  }
  const normalizedComment = String(comment || '').trim();
  if (!normalizedComment) {
    throw new Error('发货确认说明不能为空');
  }
  order.status = '供应商已确认';
  order.supplier_confirm_comment = normalizedComment;
  order.supplier_confirmed_at = new Date().toISOString();
  order.payment_validation_status = '等待付款校验结果';
  order.payment_validation_hint = order.zero_pay_exception_flag
    ? '当前已完成发货确认，并命中零付款例外场景；需等待运营/财务按冻结规则完成付款校验放行，后续仍需关注补录。'
    : '当前已完成发货确认，正在等待运营/财务完成付款校验；供应商侧仅开放结果回看，不开放付款确认。';
  order.message = '演示模式：供应商发货确认已提交';
  return { ...order };
}

module.exports = {
  confirmDemoSupplierPurchaseOrderDelivery,
  createDemoSupplierPurchaseOrderAttachment,
  createDemoSalesOrder,
  getDemoSupplierPurchaseOrderDetail,
  listDemoSupplierPurchaseOrderAttachments,
  listDemoAvailableSalesContracts,
  listDemoSalesOrders,
  listDemoSupplierPurchaseOrders,
  submitDemoSalesOrder,
  updateDemoSalesOrder,
};
