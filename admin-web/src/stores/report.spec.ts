import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchBoardTasksMock = vi.fn()
const fetchDashboardSummaryMock = vi.fn()

vi.mock('@/api/reports', () => ({
  fetchBoardTasks: fetchBoardTasksMock,
  fetchDashboardSummary: fetchDashboardSummaryMock,
}))

describe('report store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchBoardTasksMock.mockReset()
    fetchDashboardSummaryMock.mockReset()
  })

  it('异常分布包含履约滞留分类', async () => {
    fetchBoardTasksMock.mockResolvedValue({
      metric_version: 'v1',
      snapshot_time: '2026-03-06T16:20:00+08:00',
      sla_status: '正常',
      pending_supplement_count: 3,
      validation_failed_count: 2,
      qty_done_not_closed_count: 2,
      fulfillment_stagnant_count: 2,
      pending_supplement_items: [],
      validation_failed_items: [],
      qty_done_not_closed_items: [],
      fulfillment_stagnant_items: [],
      message: '业务看板查询成功',
    })

    const { useReportStore } = await import('./report')
    const store = useReportStore()
    await store.loadBoard()

    expect(store.anomalyDistribution).toHaveLength(4)
    expect(store.anomalyDistribution[3]).toMatchObject({
      key: 'stagnant',
      label: '履约滞留',
      value: 2,
    })
  })
})
