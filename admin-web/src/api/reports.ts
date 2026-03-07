import type { BoardTasksResponse, DashboardSummaryResponse } from '@/stores/report'
import {
  buildDemoAdminMultiDimReportCsv,
  demoBoardTasks,
  demoDashboardSummary,
  getDemoAdminMultiDimReport,
} from '@/mock/reports'

import { httpClient, reportsMode } from './http'

export type AdminMultiDimGroupBy = 'contract_direction' | 'doc_status' | 'refund_status'

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
