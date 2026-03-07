import type { BoardTasksResponse, DashboardSummaryResponse } from '@/stores/report'
import {
  createDemoAdminMultiDimExportTask,
  buildDemoAdminMultiDimReportCsv,
  createDemoSummaryReportRecomputeTask,
  downloadDemoAdminMultiDimExportTask,
  demoBoardTasks,
  demoDashboardSummary,
  getDemoAdminMultiDimExportTasks,
  getDemoAdminMultiDimReport,
  getDemoSummaryReportRecomputeTasks,
  retryDemoAdminMultiDimExportTask,
  retryDemoSummaryReportRecomputeTask,
} from '@/mock/reports'

import { httpClient, reportsMode } from './http'

export type AdminMultiDimGroupBy = 'contract_direction' | 'doc_status' | 'refund_status'
export type SummaryReportCode = 'dashboard_summary' | 'board_tasks' | 'light_overview'

export interface AdminMultiDimReportQuery {
  metric_version?: string
  group_by?: AdminMultiDimGroupBy
  contract_direction?: 'sales' | 'purchase'
  doc_status?: string
  refund_status?: string
  date_from?: string
  date_to?: string
}

export interface AdminMultiDimReportRow {
  dimension: string
  dimension_value: string
  receipt_net_amount: string
  payment_net_amount: string
  net_cashflow: string
  receipt_doc_count: number
  payment_doc_count: number
  pending_supplement_count: number
  refund_pending_review_count: number
}

export interface AdminMultiDimReportResponse {
  metric_version: string
  snapshot_time: string
  sla_status: string
  group_by: AdminMultiDimGroupBy
  filters: Record<string, string | null>
  total_receipt_net_amount: string
  total_payment_net_amount: string
  total_net_cashflow: string
  rows: AdminMultiDimReportRow[]
  message: string
}

export type ReportExportTaskStatus = '待处理' | '处理中' | '已完成' | '已失败'

export interface SummaryReportRecomputeResult {
  report_name: string
  snapshot_time: string
}

export interface SummaryReportRecomputeTask {
  id: number
  task_name: string
  status: ReportExportTaskStatus
  metric_version: string
  report_codes: SummaryReportCode[]
  reason: string
  requested_by: string
  requested_role_code: string
  requested_company_id: string | null
  retry_count: number
  error_message: string | null
  result_payload: Record<string, SummaryReportRecomputeResult>
  finished_at: string | null
  created_at: string
  updated_at: string
}

export interface SummaryReportRecomputeTaskCreatePayload {
  metric_version?: string
  report_codes: SummaryReportCode[]
  reason: string
}

export interface SummaryReportRecomputeTaskCreateResponse {
  task: SummaryReportRecomputeTask
  message: string
}

export interface SummaryReportRecomputeTaskListQuery {
  status?: ReportExportTaskStatus
  limit?: number
}

export interface SummaryReportRecomputeTaskListResponse {
  items: SummaryReportRecomputeTask[]
  message: string
}

export interface AdminMultiDimExportTask {
  id: number
  report_code: string
  report_name: string
  status: ReportExportTaskStatus
  export_format: string
  metric_version: string
  filters: Record<string, string | null>
  file_name: string | null
  requested_by: string
  requested_role_code: string
  requested_company_id: string | null
  retry_count: number
  download_count: number
  error_message: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export interface AdminMultiDimExportTaskCreateResponse {
  task: AdminMultiDimExportTask
  message: string
}

export interface AdminMultiDimExportTaskListResponse {
  items: AdminMultiDimExportTask[]
  message: string
}

export interface AdminMultiDimExportTaskListQuery {
  status?: ReportExportTaskStatus
  limit?: number
}

export async function fetchDashboardSummary(): Promise<DashboardSummaryResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(demoDashboardSummary)
  }
  const { data } = await httpClient.get<DashboardSummaryResponse>('/dashboard/summary')
  return data
}

export async function fetchBoardTasks(): Promise<BoardTasksResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(demoBoardTasks)
  }
  const { data } = await httpClient.get<BoardTasksResponse>('/boards/tasks')
  return data
}

export async function fetchAdminMultiDimReport(
  query: AdminMultiDimReportQuery,
): Promise<AdminMultiDimReportResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoAdminMultiDimReport(query))
  }
  const { data } = await httpClient.get<AdminMultiDimReportResponse>('/reports/admin/multi-dim', {
    params: query,
  })
  return data
}

export async function exportAdminMultiDimReportCsv(query: AdminMultiDimReportQuery): Promise<Blob> {
  if (reportsMode === 'demo') {
    return Promise.resolve(new Blob([buildDemoAdminMultiDimReportCsv(query)], { type: 'text/csv;charset=utf-8' }))
  }
  const { data } = await httpClient.get('/reports/admin/multi-dim/export', {
    params: query,
    responseType: 'blob',
  })
  return data as Blob
}

export async function createAdminMultiDimExportTask(
  query: AdminMultiDimReportQuery,
): Promise<AdminMultiDimExportTaskCreateResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(createDemoAdminMultiDimExportTask(query))
  }
  const { data } = await httpClient.post<AdminMultiDimExportTaskCreateResponse>(
    '/reports/admin/multi-dim/export-tasks',
    query,
  )
  return data
}

export async function fetchAdminMultiDimExportTasks(
  query: AdminMultiDimExportTaskListQuery = {},
): Promise<AdminMultiDimExportTaskListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoAdminMultiDimExportTasks(query))
  }
  const { data } = await httpClient.get<AdminMultiDimExportTaskListResponse>(
    '/reports/admin/multi-dim/export-tasks',
    { params: query },
  )
  return data
}

export async function downloadAdminMultiDimExportTask(taskId: number): Promise<Blob> {
  if (reportsMode === 'demo') {
    return Promise.resolve(downloadDemoAdminMultiDimExportTask(taskId))
  }
  const { data } = await httpClient.get(`/reports/admin/multi-dim/export-tasks/${taskId}/download`, {
    responseType: 'blob',
  })
  return data as Blob
}

export async function retryAdminMultiDimExportTask(
  taskId: number,
): Promise<AdminMultiDimExportTaskCreateResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(retryDemoAdminMultiDimExportTask(taskId))
  }
  const { data } = await httpClient.post<AdminMultiDimExportTaskCreateResponse>(
    `/reports/admin/multi-dim/export-tasks/${taskId}/retry`,
  )
  return data
}

export async function createSummaryReportRecomputeTask(
  payload: SummaryReportRecomputeTaskCreatePayload,
): Promise<SummaryReportRecomputeTaskCreateResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(createDemoSummaryReportRecomputeTask(payload))
  }
  const { data } = await httpClient.post<SummaryReportRecomputeTaskCreateResponse>(
    '/reports/recompute-tasks',
    payload,
  )
  return data
}

export async function fetchSummaryReportRecomputeTasks(
  query: SummaryReportRecomputeTaskListQuery = {},
): Promise<SummaryReportRecomputeTaskListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoSummaryReportRecomputeTasks(query))
  }
  const { data } = await httpClient.get<SummaryReportRecomputeTaskListResponse>(
    '/reports/recompute-tasks',
    { params: query },
  )
  return data
}

export async function retrySummaryReportRecomputeTask(
  taskId: number,
): Promise<SummaryReportRecomputeTaskCreateResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(retryDemoSummaryReportRecomputeTask(taskId))
  }
  const { data } = await httpClient.post<SummaryReportRecomputeTaskCreateResponse>(
    `/reports/recompute-tasks/${taskId}/retry`,
  )
  return data
}
