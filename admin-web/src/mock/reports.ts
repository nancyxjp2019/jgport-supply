import type { BoardTasksResponse, DashboardSummaryResponse } from '@/stores/report'
import type {
  AdminMultiDimExportTask,
  AdminMultiDimExportTaskCreateResponse,
  AdminMultiDimExportTaskListQuery,
  AdminMultiDimExportTaskListResponse,
  AdminMultiDimReportQuery,
  AdminMultiDimReportResponse,
  ReportExportTaskStatus,
  SummaryReportCode,
  SummaryReportRecomputeTask,
  SummaryReportRecomputeTaskCreatePayload,
  SummaryReportRecomputeTaskCreateResponse,
  SummaryReportRecomputeTaskListQuery,
  SummaryReportRecomputeTaskListResponse,
} from '@/api/reports'

export const demoDashboardSummary: DashboardSummaryResponse = {
  metric_version: 'v1',
  snapshot_time: '2026-03-06T16:20:00+08:00',
  sla_status: '正常',
  contract_execution_rate: '0.852300',
  actual_receipt_today: '650025.00',
  actual_payment_today: '580080.00',
  inventory_turnover_30d: '1.286500',
  threshold_alert_count: 9,
  message: '仪表盘查询成功',
}

export const demoBoardTasks: BoardTasksResponse = {
  metric_version: 'v1',
  snapshot_time: '2026-03-06T16:20:00+08:00',
  sla_status: '正常',
  pending_supplement_count: 3,
  validation_failed_count: 2,
  qty_done_not_closed_count: 2,
  fulfillment_stagnant_count: 2,
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
  fulfillment_stagnant_items: [
    {
      biz_type: 'contract',
      biz_id: 305,
      title: '合同 XS-202603-015 履约滞留',
      status: '生效中',
      contract_id: 305,
      contract_no: 'XS-202603-015',
      related_order_id: null,
      created_at: '2026-03-02T09:30:00+08:00',
      last_effect_at: '2026-03-02T09:30:00+08:00',
      days_without_effect: 4,
      scan_type: '履约滞留',
      scan_date: '2026-03-06',
    },
    {
      biz_type: 'contract',
      biz_id: 306,
      title: '合同 CG-202603-021 履约滞留',
      status: '生效中',
      contract_id: 306,
      contract_no: 'CG-202603-021',
      related_order_id: null,
      created_at: '2026-03-01T16:00:00+08:00',
      last_effect_at: '2026-03-01T16:00:00+08:00',
      days_without_effect: 5,
      scan_type: '履约滞留',
      scan_date: '2026-03-06',
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

function buildDemoExportTaskFilters(query: AdminMultiDimReportQuery): Record<string, string | null> {
  return {
    group_by: query.group_by ?? 'contract_direction',
    contract_direction: query.contract_direction ?? null,
    doc_status: query.doc_status ?? null,
    refund_status: query.refund_status ?? null,
    date_from: query.date_from ?? null,
    date_to: query.date_to ?? null,
  }
}

let demoExportTaskSeed = 903

const demoExportTasks: AdminMultiDimExportTask[] = [
  {
    id: 901,
    report_code: 'admin_multi_dim',
    report_name: '多维报表',
    status: '已完成',
    export_format: 'csv',
    metric_version: 'v1',
    filters: {
      group_by: 'contract_direction',
      contract_direction: 'sales',
      doc_status: null,
      refund_status: null,
      date_from: '2026-03-06',
      date_to: '2026-03-06',
    },
    file_name: 'multi-dim-report-task-901.csv',
    requested_by: 'DEMO-FINANCE-01',
    requested_role_code: 'finance',
    requested_company_id: 'DEMO-OPERATOR-COMPANY',
    retry_count: 0,
    download_count: 2,
    error_message: null,
    finished_at: '2026-03-06T15:42:00+08:00',
    created_at: '2026-03-06T15:40:00+08:00',
    updated_at: '2026-03-06T15:42:00+08:00',
  },
  {
    id: 902,
    report_code: 'admin_multi_dim',
    report_name: '多维报表',
    status: '已失败',
    export_format: 'csv',
    metric_version: 'v1',
    filters: {
      group_by: 'refund_status',
      contract_direction: 'purchase',
      doc_status: null,
      refund_status: '待审核',
      date_from: '2026-03-06',
      date_to: '2026-03-06',
    },
    file_name: null,
    requested_by: 'DEMO-ADMIN-01',
    requested_role_code: 'admin',
    requested_company_id: 'DEMO-OPERATOR-COMPANY',
    retry_count: 1,
    download_count: 0,
    error_message: '导出文件生成失败，请重试导出',
    finished_at: '2026-03-06T16:05:00+08:00',
    created_at: '2026-03-06T16:00:00+08:00',
    updated_at: '2026-03-06T16:05:00+08:00',
  },
]

function createDemoExportTaskRecord(
  query: AdminMultiDimReportQuery,
  status: ReportExportTaskStatus,
): AdminMultiDimExportTask {
  const now = new Date().toISOString()
  const nextId = demoExportTaskSeed
  demoExportTaskSeed += 1
  return {
    id: nextId,
    report_code: 'admin_multi_dim',
    report_name: '多维报表',
    status,
    export_format: 'csv',
    metric_version: query.metric_version ?? 'v1',
    filters: buildDemoExportTaskFilters(query),
    file_name: status === '已完成' ? `multi-dim-report-task-${nextId}.csv` : null,
    requested_by: 'DEMO-FINANCE-NEW',
    requested_role_code: 'finance',
    requested_company_id: 'DEMO-OPERATOR-COMPANY',
    retry_count: 0,
    download_count: 0,
    error_message: status === '已失败' ? '导出文件生成失败，请重试导出' : null,
    finished_at: status === '已完成' || status === '已失败' ? now : null,
    created_at: now,
    updated_at: now,
  }
}

function getDemoExportTaskOrThrow(taskId: number): AdminMultiDimExportTask {
  const task = demoExportTasks.find((item) => item.id === taskId)
  if (!task) {
    throw new Error('导出任务不存在')
  }
  return task
}

export function getDemoAdminMultiDimExportTasks(
  query: AdminMultiDimExportTaskListQuery = {},
): AdminMultiDimExportTaskListResponse {
  const filtered = demoExportTasks
    .filter((item) => !query.status || item.status === query.status)
    .slice(0, query.limit ?? 20)
  return {
    items: filtered,
    message: '导出任务列表查询成功',
  }
}

export function createDemoAdminMultiDimExportTask(
  query: AdminMultiDimReportQuery,
): AdminMultiDimExportTaskCreateResponse {
  const task = createDemoExportTaskRecord(query, '已完成')
  demoExportTasks.unshift(task)
  return {
    task,
    message: '导出任务已创建，正在后台生成文件',
  }
}

export function downloadDemoAdminMultiDimExportTask(taskId: number): Blob {
  const task = getDemoExportTaskOrThrow(taskId)
  if (task.status !== '已完成') {
    throw new Error('当前导出任务尚未生成可下载文件')
  }
  task.download_count += 1
  task.updated_at = new Date().toISOString()
  return new Blob(
    [
      buildDemoAdminMultiDimReportCsv({
        metric_version: task.metric_version,
        group_by: (task.filters.group_by as AdminMultiDimReportQuery['group_by']) ?? 'contract_direction',
        contract_direction: (task.filters.contract_direction as AdminMultiDimReportQuery['contract_direction']) ?? undefined,
        doc_status: task.filters.doc_status ?? undefined,
        refund_status: task.filters.refund_status ?? undefined,
        date_from: task.filters.date_from ?? undefined,
        date_to: task.filters.date_to ?? undefined,
      }),
    ],
    { type: 'text/csv;charset=utf-8' },
  )
}

export function retryDemoAdminMultiDimExportTask(
  taskId: number,
): AdminMultiDimExportTaskCreateResponse {
  const task = getDemoExportTaskOrThrow(taskId)
  if (task.status !== '已失败') {
    throw new Error('当前导出任务不支持重试')
  }
  const now = new Date().toISOString()
  task.status = '已完成'
  task.retry_count += 1
  task.error_message = null
  task.file_name = `multi-dim-report-task-${task.id}-retry.csv`
  task.finished_at = now
  task.updated_at = now
  return {
    task,
    message: '导出任务已重新发起，正在后台生成文件',
  }
}

const summaryReportLabels: Record<SummaryReportCode, string> = {
  dashboard_summary: '经营仪表盘',
  board_tasks: '业务看板',
  light_overview: '轻量报表',
}

let demoRecomputeTaskSeed = 1103

const demoSummaryReportRecomputeTasks: SummaryReportRecomputeTask[] = [
  {
    id: 1101,
    task_name: '汇总报表口径重算',
    status: '已完成',
    metric_version: 'v1',
    report_codes: ['dashboard_summary', 'board_tasks'],
    reason: '修正合同履约补录后刷新汇总快照',
    requested_by: 'DEMO-FINANCE-01',
    requested_role_code: 'finance',
    requested_company_id: 'DEMO-OPERATOR-COMPANY',
    retry_count: 0,
    error_message: null,
    result_payload: {
      dashboard_summary: {
        report_name: '经营仪表盘',
        snapshot_time: '2026-03-07T10:35:00+08:00',
      },
      board_tasks: {
        report_name: '业务看板',
        snapshot_time: '2026-03-07T10:35:20+08:00',
      },
    },
    finished_at: '2026-03-07T10:35:20+08:00',
    created_at: '2026-03-07T10:34:50+08:00',
    updated_at: '2026-03-07T10:35:20+08:00',
  },
  {
    id: 1102,
    task_name: '汇总报表口径重算',
    status: '已失败',
    metric_version: 'v1',
    report_codes: ['light_overview'],
    reason: '修正移动端经营金额后补刷轻量报表',
    requested_by: 'DEMO-ADMIN-01',
    requested_role_code: 'admin',
    requested_company_id: 'DEMO-OPERATOR-COMPANY',
    retry_count: 1,
    error_message: '轻量报表快照重算失败，请稍后重试',
    result_payload: {},
    finished_at: '2026-03-07T11:05:00+08:00',
    created_at: '2026-03-07T11:00:00+08:00',
    updated_at: '2026-03-07T11:05:00+08:00',
  },
]

function buildDemoSummaryReportResult(
  reportCodes: SummaryReportCode[],
  now: string,
): Record<string, { report_name: string; snapshot_time: string }> {
  return Object.fromEntries(
    reportCodes.map((reportCode, index) => {
      const snapshotTime = new Date(Date.now() + index * 1000).toISOString()
      return [
        reportCode,
        {
          report_name: summaryReportLabels[reportCode],
          snapshot_time: index === 0 ? now : snapshotTime,
        },
      ]
    }),
  )
}

function getDemoSummaryReportRecomputeTaskOrThrow(taskId: number): SummaryReportRecomputeTask {
  const task = demoSummaryReportRecomputeTasks.find((item) => item.id === taskId)
  if (!task) {
    throw new Error('重算任务不存在')
  }
  return task
}

export function getDemoSummaryReportRecomputeTasks(
  query: SummaryReportRecomputeTaskListQuery = {},
): SummaryReportRecomputeTaskListResponse {
  const filtered = demoSummaryReportRecomputeTasks
    .filter((item) => !query.status || item.status === query.status)
    .slice(0, query.limit ?? 20)
  return {
    items: filtered,
    message: '重算任务列表查询成功',
  }
}

export function createDemoSummaryReportRecomputeTask(
  payload: SummaryReportRecomputeTaskCreatePayload,
): SummaryReportRecomputeTaskCreateResponse {
  const now = new Date().toISOString()
  const task: SummaryReportRecomputeTask = {
    id: demoRecomputeTaskSeed,
    task_name: '汇总报表口径重算',
    status: '已完成',
    metric_version: payload.metric_version ?? 'v1',
    report_codes: payload.report_codes,
    reason: payload.reason,
    requested_by: 'DEMO-FINANCE-NEW',
    requested_role_code: 'finance',
    requested_company_id: 'DEMO-OPERATOR-COMPANY',
    retry_count: 0,
    error_message: null,
    result_payload: buildDemoSummaryReportResult(payload.report_codes, now),
    finished_at: now,
    created_at: now,
    updated_at: now,
  }
  demoRecomputeTaskSeed += 1
  demoSummaryReportRecomputeTasks.unshift(task)
  return {
    task,
    message: '重算任务已创建，正在后台执行',
  }
}

export function retryDemoSummaryReportRecomputeTask(
  taskId: number,
): SummaryReportRecomputeTaskCreateResponse {
  const task = getDemoSummaryReportRecomputeTaskOrThrow(taskId)
  if (task.status !== '已失败') {
    throw new Error('当前重算任务不支持重试')
  }
  const now = new Date().toISOString()
  task.status = '已完成'
  task.retry_count += 1
  task.error_message = null
  task.result_payload = buildDemoSummaryReportResult(task.report_codes, now)
  task.finished_at = now
  task.updated_at = now
  return {
    task,
    message: '重算任务已重新发起，正在后台执行',
  }
}
