import type { BoardTasksResponse, DashboardSummaryResponse } from '@/stores/report'
import { demoBoardTasks, demoDashboardSummary } from '@/mock/reports'

import { httpClient, reportsMode } from './http'

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
