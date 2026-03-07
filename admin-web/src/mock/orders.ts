export interface DemoSalesOrderItem {
  id: number
  order_no: string
  sales_contract_id: number
  sales_contract_no: string
  oil_product_id: string
  qty_ordered: string
  unit_price: string
  status: string
  submit_comment: string | null
  ops_comment: string | null
  finance_comment: string | null
  purchase_order_id: number | null
  submitted_at: string | null
  created_at: string
}

export interface DemoSalesOrderListResponse {
  items: DemoSalesOrderItem[]
  total: number
  message: string
}

export interface DemoSalesOrderDetailResponse extends DemoSalesOrderItem {
  message: string
  generated_task_count: number
}

const DEMO_SALES_ORDERS: DemoSalesOrderDetailResponse[] = [
  {
    id: 6101,
    order_no: 'SO-DEMO-OPS-6101',
    sales_contract_id: 4201,
    sales_contract_no: 'XS-202603-001',
    oil_product_id: 'OIL-92',
    qty_ordered: '20.000',
    unit_price: '6500.25',
    status: '待运营审批',
    submit_comment: 'AUTO-TEST-客户提交运营审批',
    ops_comment: null,
    finance_comment: null,
    purchase_order_id: null,
    submitted_at: '2026-03-07T09:10:00+08:00',
    created_at: '2026-03-07T08:55:00+08:00',
    generated_task_count: 0,
    message: '演示模式：销售订单详情查询成功',
  },
  {
    id: 6102,
    order_no: 'SO-DEMO-FIN-6102',
    sales_contract_id: 4202,
    sales_contract_no: 'XS-202603-002',
    oil_product_id: 'OIL-95',
    qty_ordered: '18.500',
    unit_price: '6720.80',
    status: '待财务审批',
    submit_comment: 'AUTO-TEST-客户提交财务审批',
    ops_comment: 'AUTO-TEST-运营审批通过',
    finance_comment: null,
    purchase_order_id: null,
    submitted_at: '2026-03-07T08:20:00+08:00',
    created_at: '2026-03-07T08:00:00+08:00',
    generated_task_count: 0,
    message: '演示模式：销售订单详情查询成功',
  },
  {
    id: 6103,
    order_no: 'SO-DEMO-DONE-6103',
    sales_contract_id: 4203,
    sales_contract_no: 'XS-202603-003',
    oil_product_id: 'OIL-0',
    qty_ordered: '12.000',
    unit_price: '5988.60',
    status: '已衍生采购订单',
    submit_comment: 'AUTO-TEST-客户提交审批',
    ops_comment: 'AUTO-TEST-运营审批通过',
    finance_comment: 'AUTO-TEST-财务审批通过',
    purchase_order_id: 9103,
    submitted_at: '2026-03-06T15:10:00+08:00',
    created_at: '2026-03-06T14:30:00+08:00',
    generated_task_count: 2,
    message: '演示模式：销售订单详情查询成功',
  },
]

function cloneOrder(item: DemoSalesOrderDetailResponse): DemoSalesOrderDetailResponse {
  return { ...item }
}

export function listDemoSalesOrders(status?: string): DemoSalesOrderListResponse {
  const normalized = String(status || '').trim()
  const items = normalized
    ? DEMO_SALES_ORDERS.filter((item) => item.status === normalized)
    : DEMO_SALES_ORDERS
  return {
    items: items.map(cloneOrder),
    total: items.length,
    message: '演示模式：销售订单列表查询成功',
  }
}

export function getDemoSalesOrderDetail(orderId: number): DemoSalesOrderDetailResponse {
  const target = DEMO_SALES_ORDERS.find((item) => item.id === Number(orderId))
  if (!target) {
    throw new Error('当前销售订单不存在，请刷新后重试')
  }
  return cloneOrder(target)
}

export function approveDemoSalesOrderByOps(orderId: number, result: boolean, comment: string): DemoSalesOrderDetailResponse {
  const target = DEMO_SALES_ORDERS.find((item) => item.id === Number(orderId))
  if (!target) {
    throw new Error('当前销售订单不存在，请刷新后重试')
  }
  if (target.status !== '待运营审批') {
    throw new Error('当前销售订单状态不允许执行运营审批')
  }
  const normalizedComment = String(comment || '').trim()
  if (!normalizedComment) {
    throw new Error('运营审批意见不能为空')
  }
  target.ops_comment = normalizedComment
  if (result) {
    target.status = '待财务审批'
    target.message = '演示模式：运营审批通过'
  } else {
    target.status = '草稿'
    target.message = '演示模式：运营审批驳回，订单已回退草稿'
  }
  return cloneOrder(target)
}

export function approveDemoSalesOrderByFinance(
  orderId: number,
  payload: {
    result: boolean
    purchase_contract_id?: number | null
    actual_receipt_amount?: number | null
    actual_pay_amount?: number | null
    comment: string
  },
): DemoSalesOrderDetailResponse {
  const target = DEMO_SALES_ORDERS.find((item) => item.id === Number(orderId))
  if (!target) {
    throw new Error('当前销售订单不存在，请刷新后重试')
  }
  if (target.status !== '待财务审批') {
    throw new Error('当前销售订单状态不允许执行财务审批')
  }
  const normalizedComment = String(payload.comment || '').trim()
  if (!normalizedComment) {
    throw new Error('财务审批意见不能为空')
  }
  target.finance_comment = normalizedComment
  if (!payload.result) {
    target.status = '驳回'
    target.message = '演示模式：财务审批驳回'
    target.generated_task_count = 0
    target.purchase_order_id = null
    return cloneOrder(target)
  }
  if (!payload.purchase_contract_id) {
    throw new Error('财务审批通过时必须填写采购合同ID')
  }
  if (payload.actual_receipt_amount == null || payload.actual_pay_amount == null) {
    throw new Error('财务审批通过时必须填写实收金额与实付金额')
  }
  target.status = '已衍生采购订单'
  target.purchase_order_id = 9500 + target.id
  target.generated_task_count = 2
  target.message = '演示模式：财务审批通过，已生成采购订单与收付款任务'
  return cloneOrder(target)
}
