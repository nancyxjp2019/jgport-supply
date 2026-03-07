import type { BoardTasksResponse, DashboardSummaryResponse } from '@/stores/report'
import type { AdminMultiDimReportQuery, AdminMultiDimReportResponse } from '@/api/reports'

export const demoDashboardSummary: DashboardSummaryResponse = {
  metric_version: 'v1',
  snapshot_time: '2026-03-06T16:20:00+08:00',
  sla_status: '正常',
  contract_execution_rate: '0.852300',
  actual_receipt_today: '650025.00',
  actual_payment_today: '580080.00',
  inventory_turnover_30d: '1.286500',
  threshold_alert_count: 7,
  message: '仪表盘查询成功',
}

export const demoBoardTasks: BoardTasksResponse = {
  metric_version: 'v1',
  snapshot_time: '2026-03-06T16:20:00+08:00',
  sla_status: '正常',
  pending_supplement_count: 3,
  validation_failed_count: 2,
  qty_done_not_closed_count: 2,
  pending_supplement_items: [
    {
      biz_type: 'receipt_doc',
      biz_id: 101,
      title: '收款单 REC-20260306-101 待补录金额',
      status: '待补录金额',
      contract_id: 301,
      contract_no: 'XS-202603-001',
      related_order_id: 501,
      created_at: '2026-03-06T09:20:00+08:00',
    },
    {
      biz_type: 'payment_doc',
      biz_id: 102,
      title: '付款单 PAY-20260306-102 待补录金额',
      status: '待补录金额',
      contract_id: 302,
      contract_no: 'CG-202603-009',
      related_order_id: 502,
      created_at: '2026-03-06T10:15:00+08:00',
    },
  ],
  validation_failed_items: [
    {
      biz_type: 'outbound_doc',
      biz_id: 201,
      title: '出库单 OUT-20260306-201 校验失败',
      status: '校验失败',
      contract_id: 301,
      contract_no: 'XS-202603-001',
      related_order_id: 501,
      created_at: '2026-03-06T11:10:00+08:00',
    },
    {
      biz_type: 'inbound_doc',
      biz_id: 202,
      title: '入库单 INB-20260306-202 校验失败',
      status: '校验失败',
      contract_id: 303,
      contract_no: 'CG-202603-011',
      related_order_id: null,
      created_at: '2026-03-06T13:40:00+08:00',
    },
  ],
  qty_done_not_closed_items: [
    {
      biz_type: 'contract',
      biz_id: 301,
      title: '合同 XS-202603-001 数量履约完成待关闭',
      status: '数量履约完成',
      contract_id: 301,
      contract_no: 'XS-202603-001',
      related_order_id: null,
      created_at: '2026-03-06T14:05:00+08:00',
    },
  ],
  message: '业务看板查询成功',
}

interface DemoMultiDimSourceItem {
  doc_kind: 'receipt' | 'payment'
  contract_direction: 'sales' | 'purchase'
  doc_status: string
  refund_status: string
  net_amount: number
  created_at: string
}

const demoMultiDimSourceItems: DemoMultiDimSourceItem[] = [
  {
    doc_kind: 'receipt',
    contract_direction: 'sales',
    doc_status: '已确认',
    refund_status: '未退款',
    net_amount: 325000,
    created_at: '2026-03-06T09:25:00+08:00',
  },
  {
    doc_kind: 'receipt',
    contract_direction: 'sales',
    doc_status: '待补录金额',
    refund_status: '未退款',
    net_amount: 0,
    created_at: '2026-03-06T10:10:00+08:00',
  },
  {
    doc_kind: 'payment',
    contract_direction: 'purchase',
    doc_status: '已确认',
    refund_status: '待审核',
    net_amount: 205000,
    created_at: '2026-03-06T11:20:00+08:00',
  },
  {
    doc_kind: 'payment',
    contract_direction: 'purchase',
    doc_status: '已核销',
    refund_status: '驳回',
    net_amount: 128000,
    created_at: '2026-03-06T14:10:00+08:00',
  },
  {
    doc_kind: 'payment',
    contract_direction: 'purchase',
    doc_status: '待补录金额',
    refund_status: '未退款',
    net_amount: 0,
    created_at: '2026-03-06T15:40:00+08:00',
  },
]

function normalizeGroupBy(groupBy?: string): 'contract_direction' | 'doc_status' | 'refund_status' {
  if (groupBy === 'doc_status' || groupBy === 'refund_status') {
    return groupBy
  }
  return 'contract_direction'
}

function resolveGroupValue(
  groupBy: 'contract_direction' | 'doc_status' | 'refund_status',
  item: DemoMultiDimSourceItem,
): string {
  if (groupBy === 'contract_direction') {
    return item.contract_direction === 'sales' ? '销售' : '采购'
  }
  if (groupBy === 'doc_status') {
    return item.doc_status
  }
  return item.refund_status
}

function resolveDateFilter(timestamp: string, dateFrom?: string, dateTo?: string): boolean {
  const value = timestamp.slice(0, 10)
  if (dateFrom && value < dateFrom) {
    return false
  }
  if (dateTo && value > dateTo) {
    return false
  }
  return true
}

function toMoneyText(value: number): string {
  return value.toFixed(2)
}

export function getDemoAdminMultiDimReport(query: AdminMultiDimReportQuery): AdminMultiDimReportResponse {
  const groupBy = normalizeGroupBy(query.group_by)
  const filtered = demoMultiDimSourceItems.filter((item) => {
    if (query.contract_direction && item.contract_direction !== query.contract_direction) {
      return false
    }
    if (query.doc_status && item.doc_status !== query.doc_status) {
      return false
    }
    if (query.refund_status && item.refund_status !== query.refund_status) {
      return false
    }
    return resolveDateFilter(item.created_at, query.date_from, query.date_to)
  })

  const bucketMap = new Map<string, {
    dimension: string
    dimension_value: string
    receipt_net_amount: number
    payment_net_amount: number
    receipt_doc_count: number
    payment_doc_count: number
    pending_supplement_count: number
    refund_pending_review_count: number
  }>()

  filtered.forEach((item) => {
    const groupValue = resolveGroupValue(groupBy, item)
    if (!bucketMap.has(groupValue)) {
      bucketMap.set(groupValue, {
        dimension: groupBy,
        dimension_value: groupValue,
        receipt_net_amount: 0,
        payment_net_amount: 0,
        receipt_doc_count: 0,
        payment_doc_count: 0,
        pending_supplement_count: 0,
        refund_pending_review_count: 0,
      })
    }
    const bucket = bucketMap.get(groupValue)
    if (!bucket) {
      return
    }
    if (item.doc_kind === 'receipt') {
      bucket.receipt_net_amount += item.net_amount
      bucket.receipt_doc_count += 1
    } else {
      bucket.payment_net_amount += item.net_amount
      bucket.payment_doc_count += 1
    }
    if (item.doc_status === '待补录金额') {
      bucket.pending_supplement_count += 1
    }
    if (item.refund_status === '待审核') {
      bucket.refund_pending_review_count += 1
    }
  })

  const rows = Array.from(bucketMap.values())
    .sort((a, b) => a.dimension_value.localeCompare(b.dimension_value, 'zh-CN'))
    .map((item) => {
      const netCashflow = item.receipt_net_amount - item.payment_net_amount
      return {
        ...item,
        receipt_net_amount: toMoneyText(item.receipt_net_amount),
        payment_net_amount: toMoneyText(item.payment_net_amount),
        net_cashflow: toMoneyText(netCashflow),
      }
    })

  const totalReceipt = rows.reduce((sum, row) => sum + Number.parseFloat(row.receipt_net_amount), 0)
  const totalPayment = rows.reduce((sum, row) => sum + Number.parseFloat(row.payment_net_amount), 0)

  return {
    metric_version: 'v1',
    snapshot_time: '2026-03-06T16:35:00+08:00',
    sla_status: '正常',
    group_by: groupBy,
    filters: {
      contract_direction: query.contract_direction ?? null,
      doc_status: query.doc_status ?? null,
      refund_status: query.refund_status ?? null,
      date_from: query.date_from ?? null,
      date_to: query.date_to ?? null,
    },
    total_receipt_net_amount: toMoneyText(totalReceipt),
    total_payment_net_amount: toMoneyText(totalPayment),
    total_net_cashflow: toMoneyText(totalReceipt - totalPayment),
    rows,
    message: '后台多维报表查询成功',
  }
}

export function buildDemoAdminMultiDimReportCsv(query: AdminMultiDimReportQuery): string {
  const report = getDemoAdminMultiDimReport(query)
  const lines = [
    '维度,维度值,收款净额,付款净额,资金净流入,收款单数,付款单数,待补录数量,待审核退款数量',
  ]
  report.rows.forEach((row) => {
    lines.push(
      [
        row.dimension,
        row.dimension_value,
        row.receipt_net_amount,
        row.payment_net_amount,
        row.net_cashflow,
        row.receipt_doc_count,
        row.payment_doc_count,
        row.pending_supplement_count,
        row.refund_pending_review_count,
      ].join(','),
    )
  })
  return `\ufeff${lines.join('\n')}`
}
