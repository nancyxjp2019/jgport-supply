import type {
  FundDocConfirmPayload,
  PaymentDocDetailResponse,
  PaymentDocListResponse,
  PaymentDocSupplementPayload,
  ReceiptDocDetailResponse,
  ReceiptDocListResponse,
  ReceiptDocSupplementPayload,
} from '@/api/funds'

interface DemoPaymentDoc extends PaymentDocDetailResponse {
  rule11_exempt: boolean
  rule14_pass: boolean
}

interface DemoReceiptDoc extends ReceiptDocDetailResponse {
  rule14_pass: boolean
}

const DEMO_PAYMENT_DOCS: DemoPaymentDoc[] = [
  {
    id: 8101,
    doc_no: 'PAY-DEMO-8101',
    doc_type: 'NORMAL',
    contract_id: 5201,
    purchase_order_id: 9101,
    amount_actual: '0.00',
    status: '草稿',
    voucher_required: false,
    voucher_exempt_reason: '例外放行（需后补付款单）',
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: null,
    created_at: '2026-03-08T09:15:00+08:00',
    voucher_file_paths: [],
    message: '演示模式：付款单详情查询成功',
    rule11_exempt: true,
    rule14_pass: false,
  },
  {
    id: 8102,
    doc_no: 'PAY-DEMO-8102',
    doc_type: 'NORMAL',
    contract_id: 5202,
    purchase_order_id: 9102,
    amount_actual: '0.00',
    status: '待补录金额',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: null,
    created_at: '2026-03-08T08:40:00+08:00',
    voucher_file_paths: [],
    message: '演示模式：付款单详情查询成功',
    rule11_exempt: false,
    rule14_pass: false,
  },
  {
    id: 8103,
    doc_no: 'PAY-DEMO-8103',
    doc_type: 'DEPOSIT',
    contract_id: 5203,
    purchase_order_id: null,
    amount_actual: '50000.00',
    status: '已确认',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: '2026-03-07T17:40:00+08:00',
    created_at: '2026-03-07T16:30:00+08:00',
    voucher_file_paths: ['AUTO-TEST-/funds/pay-voucher-8103.jpg'],
    message: '演示模式：付款单详情查询成功',
    rule11_exempt: false,
    rule14_pass: false,
  },
]

const DEMO_RECEIPT_DOCS: DemoReceiptDoc[] = [
  {
    id: 8201,
    doc_no: 'REC-DEMO-8201',
    doc_type: 'NORMAL',
    contract_id: 4201,
    sales_order_id: 6101,
    amount_actual: '0.00',
    status: '草稿',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: null,
    created_at: '2026-03-08T09:05:00+08:00',
    voucher_file_paths: [],
    message: '演示模式：收款单详情查询成功',
    rule14_pass: true,
  },
  {
    id: 8202,
    doc_no: 'REC-DEMO-8202',
    doc_type: 'NORMAL',
    contract_id: 4202,
    sales_order_id: 6102,
    amount_actual: '0.00',
    status: '待补录金额',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: null,
    created_at: '2026-03-08T08:30:00+08:00',
    voucher_file_paths: [],
    message: '演示模式：收款单详情查询成功',
    rule14_pass: false,
  },
  {
    id: 8203,
    doc_no: 'REC-DEMO-8203',
    doc_type: 'DEPOSIT',
    contract_id: 4203,
    sales_order_id: null,
    amount_actual: '50000.00',
    status: '已确认',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: '2026-03-07T17:20:00+08:00',
    created_at: '2026-03-07T16:10:00+08:00',
    voucher_file_paths: ['AUTO-TEST-/funds/receipt-voucher-8203.jpg'],
    message: '演示模式：收款单详情查询成功',
    rule14_pass: false,
  },
]

let paymentSeed = 8900
let receiptSeed = 9800

function toAmountText(value: number): string {
  return value.toFixed(2)
}

function normalizePositiveNumber(value: number, fieldLabel: string): number {
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(`${fieldLabel}必须大于0`)
  }
  return value
}

function normalizeConfirmAmount(value: number): number {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error('确认金额必须大于等于0')
  }
  return value
}

function normalizeVoucherFiles(voucherFiles: string[]): string[] {
  const normalized: string[] = []
  const visited = new Set<string>()
  for (const item of voucherFiles) {
    const path = String(item || '').trim()
    if (!path) {
      continue
    }
    if (visited.has(path)) {
      continue
    }
    visited.add(path)
    normalized.push(path)
  }
  return normalized
}

function clonePaymentDoc(item: DemoPaymentDoc): PaymentDocDetailResponse {
  return {
    id: item.id,
    doc_no: item.doc_no,
    doc_type: item.doc_type,
    contract_id: item.contract_id,
    purchase_order_id: item.purchase_order_id,
    amount_actual: item.amount_actual,
    status: item.status,
    voucher_required: item.voucher_required,
    voucher_exempt_reason: item.voucher_exempt_reason,
    refund_status: item.refund_status,
    refund_amount: item.refund_amount,
    confirmed_at: item.confirmed_at,
    created_at: item.created_at,
    voucher_file_paths: [...item.voucher_file_paths],
    message: item.message,
  }
}

function cloneReceiptDoc(item: DemoReceiptDoc): ReceiptDocDetailResponse {
  return {
    id: item.id,
    doc_no: item.doc_no,
    doc_type: item.doc_type,
    contract_id: item.contract_id,
    sales_order_id: item.sales_order_id,
    amount_actual: item.amount_actual,
    status: item.status,
    voucher_required: item.voucher_required,
    voucher_exempt_reason: item.voucher_exempt_reason,
    refund_status: item.refund_status,
    refund_amount: item.refund_amount,
    confirmed_at: item.confirmed_at,
    created_at: item.created_at,
    voucher_file_paths: [...item.voucher_file_paths],
    message: item.message,
  }
}

function getPaymentDocOrThrow(docId: number): DemoPaymentDoc {
  const target = DEMO_PAYMENT_DOCS.find((item) => item.id === Number(docId))
  if (!target) {
    throw new Error('当前付款单不存在，请刷新后重试')
  }
  return target
}

function getReceiptDocOrThrow(docId: number): DemoReceiptDoc {
  const target = DEMO_RECEIPT_DOCS.find((item) => item.id === Number(docId))
  if (!target) {
    throw new Error('当前收款单不存在，请刷新后重试')
  }
  return target
}

export function listDemoPaymentDocs(status?: string): PaymentDocListResponse {
  const normalizedStatus = String(status || '').trim()
  const items = normalizedStatus
    ? DEMO_PAYMENT_DOCS.filter((item) => item.status === normalizedStatus)
    : DEMO_PAYMENT_DOCS
  return {
    items: items.map((item) => clonePaymentDoc(item)),
    total: items.length,
    message: '演示模式：付款单列表查询成功',
  }
}

export function listDemoReceiptDocs(status?: string): ReceiptDocListResponse {
  const normalizedStatus = String(status || '').trim()
  const items = normalizedStatus
    ? DEMO_RECEIPT_DOCS.filter((item) => item.status === normalizedStatus)
    : DEMO_RECEIPT_DOCS
  return {
    items: items.map((item) => cloneReceiptDoc(item)),
    total: items.length,
    message: '演示模式：收款单列表查询成功',
  }
}

export function getDemoPaymentDocDetail(docId: number): PaymentDocDetailResponse {
  return clonePaymentDoc(getPaymentDocOrThrow(docId))
}

export function getDemoReceiptDocDetail(docId: number): ReceiptDocDetailResponse {
  return cloneReceiptDoc(getReceiptDocOrThrow(docId))
}

export function createDemoPaymentSupplement(payload: PaymentDocSupplementPayload): PaymentDocDetailResponse {
  const contractId = normalizePositiveNumber(payload.contract_id, '采购合同ID')
  const purchaseOrderId = normalizePositiveNumber(payload.purchase_order_id, '采购订单ID')
  const amountActual = normalizePositiveNumber(payload.amount_actual, '补录付款金额')
  paymentSeed += 1
  const nowText = new Date().toISOString()
  const created: DemoPaymentDoc = {
    id: paymentSeed,
    doc_no: `PAY-DEMO-${paymentSeed}`,
    doc_type: 'NORMAL',
    contract_id: Number(contractId),
    purchase_order_id: Number(purchaseOrderId),
    amount_actual: toAmountText(amountActual),
    status: '草稿',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: null,
    created_at: nowText,
    voucher_file_paths: [],
    message: '演示模式：付款单草稿已补录',
    rule11_exempt: false,
    rule14_pass: false,
  }
  DEMO_PAYMENT_DOCS.unshift(created)
  return clonePaymentDoc(created)
}

export function createDemoReceiptSupplement(payload: ReceiptDocSupplementPayload): ReceiptDocDetailResponse {
  const contractId = normalizePositiveNumber(payload.contract_id, '销售合同ID')
  const salesOrderId = normalizePositiveNumber(payload.sales_order_id, '销售订单ID')
  const amountActual = normalizePositiveNumber(payload.amount_actual, '补录收款金额')
  receiptSeed += 1
  const nowText = new Date().toISOString()
  const created: DemoReceiptDoc = {
    id: receiptSeed,
    doc_no: `REC-DEMO-${receiptSeed}`,
    doc_type: 'NORMAL',
    contract_id: Number(contractId),
    sales_order_id: Number(salesOrderId),
    amount_actual: toAmountText(amountActual),
    status: '草稿',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: null,
    created_at: nowText,
    voucher_file_paths: [],
    message: '演示模式：收款单草稿已补录',
    rule14_pass: false,
  }
  DEMO_RECEIPT_DOCS.unshift(created)
  return cloneReceiptDoc(created)
}

export function confirmDemoPaymentDoc(docId: number, payload: FundDocConfirmPayload): PaymentDocDetailResponse {
  const target = getPaymentDocOrThrow(docId)
  if (!['草稿', '待补录金额'].includes(target.status)) {
    throw new Error('当前付款单状态不允许确认')
  }
  const amountActual = normalizeConfirmAmount(payload.amount_actual)
  const voucherFiles = normalizeVoucherFiles(payload.voucher_files || [])
  target.amount_actual = toAmountText(amountActual)

  if (amountActual > 0) {
    if (!voucherFiles.length) {
      throw new Error('非0金额付款单必须上传付款凭证')
    }
    target.status = '已确认'
    target.voucher_required = true
    target.voucher_exempt_reason = null
    target.confirmed_at = new Date().toISOString()
    target.voucher_file_paths = voucherFiles
    target.message = '演示模式：付款单已确认'
    return clonePaymentDoc(target)
  }

  if (target.rule11_exempt) {
    target.status = '已确认'
    target.voucher_required = false
    target.voucher_exempt_reason = '例外放行（需后补付款单）'
    target.confirmed_at = new Date().toISOString()
    target.voucher_file_paths = []
    target.message = '演示模式：付款单已按规则11例外确认'
    return clonePaymentDoc(target)
  }

  if (target.rule14_pass) {
    target.status = '已确认'
    target.voucher_required = false
    target.voucher_exempt_reason = '保证金覆盖放行（规则14）'
    target.confirmed_at = new Date().toISOString()
    target.voucher_file_paths = []
    target.message = '演示模式：付款单已按规则14免凭证确认'
    return clonePaymentDoc(target)
  }

  target.status = '待补录金额'
  target.voucher_required = true
  target.voucher_exempt_reason = null
  target.confirmed_at = null
  target.voucher_file_paths = []
  target.message = '演示模式：0金额付款不满足放行条件，已转待补录金额'
  return clonePaymentDoc(target)
}

export function confirmDemoReceiptDoc(docId: number, payload: FundDocConfirmPayload): ReceiptDocDetailResponse {
  const target = getReceiptDocOrThrow(docId)
  if (!['草稿', '待补录金额'].includes(target.status)) {
    throw new Error('当前收款单状态不允许确认')
  }
  const amountActual = normalizeConfirmAmount(payload.amount_actual)
  const voucherFiles = normalizeVoucherFiles(payload.voucher_files || [])
  target.amount_actual = toAmountText(amountActual)

  if (amountActual > 0) {
    if (!voucherFiles.length) {
      throw new Error('非0金额收款单必须上传收款凭证')
    }
    target.status = '已确认'
    target.voucher_required = true
    target.voucher_exempt_reason = null
    target.confirmed_at = new Date().toISOString()
    target.voucher_file_paths = voucherFiles
    target.message = '演示模式：收款单已确认'
    return cloneReceiptDoc(target)
  }

  if (target.rule14_pass) {
    target.status = '已确认'
    target.voucher_required = false
    target.voucher_exempt_reason = '保证金覆盖放行（规则14）'
    target.confirmed_at = new Date().toISOString()
    target.voucher_file_paths = []
    target.message = '演示模式：收款单已按规则14免凭证确认'
    return cloneReceiptDoc(target)
  }

  target.status = '待补录金额'
  target.voucher_required = true
  target.voucher_exempt_reason = null
  target.confirmed_at = null
  target.voucher_file_paths = []
  target.message = '演示模式：0金额收款不满足放行条件，已转待补录金额'
  return cloneReceiptDoc(target)
}
