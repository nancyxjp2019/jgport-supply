import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchBoardTasks, fetchDashboardSummary } from '@/api/reports'

export interface DashboardSummaryResponse {
  metric_version: string
  snapshot_time: string
  sla_status: string
  contract_execution_rate: string
  actual_receipt_today: string
  actual_payment_today: string
  inventory_turnover_30d: string
  threshold_alert_count: number
  message: string
}

export interface BoardTaskItem {
  biz_type: string
  biz_id: number
  title: string
  status: string
  contract_id: number | null
  contract_no: string | null
  related_order_id: number | null
  created_at: string | null
}

export interface BoardTasksResponse {
  metric_version: string
  snapshot_time: string
  sla_status: string
  pending_supplement_count: number
  validation_failed_count: number
  qty_done_not_closed_count: number
  pending_supplement_items: BoardTaskItem[]
  validation_failed_items: BoardTaskItem[]
  qty_done_not_closed_items: BoardTaskItem[]
  message: string
}

export const useReportStore = defineStore('report', () => {
  const dashboard = ref<DashboardSummaryResponse | null>(null)
  const board = ref<BoardTasksResponse | null>(null)
  const dashboardLoading = ref(false)
  const boardLoading = ref(false)
  const dashboardError = ref('')
  const boardError = ref('')

  async function loadDashboard() {
    dashboardLoading.value = true
    dashboardError.value = ''
    try {
      dashboard.value = await fetchDashboardSummary()
    } catch (error) {
      dashboardError.value = error instanceof Error ? error.message : '仪表盘加载失败'
    } finally {
      dashboardLoading.value = false
    }
  }

  async function loadBoard() {
    boardLoading.value = true
    boardError.value = ''
    try {
      board.value = await fetchBoardTasks()
    } catch (error) {
      boardError.value = error instanceof Error ? error.message : '业务看板加载失败'
    } finally {
      boardLoading.value = false
    }
  }

  const anomalyDistribution = computed(() => {
    if (!board.value) {
      return []
    }
    const total =
      board.value.pending_supplement_count +
      board.value.validation_failed_count +
      board.value.qty_done_not_closed_count
    return [
      {
        key: 'pending',
        label: '待补录金额',
        value: board.value.pending_supplement_count,
        ratio: total > 0 ? board.value.pending_supplement_count / total : 0,
      },
      {
        key: 'failed',
        label: '校验失败',
        value: board.value.validation_failed_count,
        ratio: total > 0 ? board.value.validation_failed_count / total : 0,
      },
      {
        key: 'qtydone',
        label: '数量履约完成未关闭',
        value: board.value.qty_done_not_closed_count,
        ratio: total > 0 ? board.value.qty_done_not_closed_count / total : 0,
      },
    ]
  })

  return {
    anomalyDistribution,
    board,
    boardError,
    boardLoading,
    dashboard,
    dashboardError,
    dashboardLoading,
    loadBoard,
    loadDashboard,
  }
})
