import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchDashboardSummaryMock = vi.fn()
const fetchBoardTasksMock = vi.fn()

const mountOptions = {
  global: {
    directives: {
      loading: () => undefined,
    },
  },
}

vi.mock('@/api/reports', () => ({
  fetchBoardTasks: fetchBoardTasksMock,
  fetchDashboardSummary: fetchDashboardSummaryMock,
}))

describe('OverviewView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchDashboardSummaryMock.mockReset()
    fetchBoardTasksMock.mockReset()
  })

  it('挂载后加载仪表盘与业务看板并展示核心指标', async () => {
    fetchDashboardSummaryMock.mockResolvedValue({
      metric_version: 'v1',
      snapshot_time: '2026-03-08T10:00:00+08:00',
      sla_status: '正常',
      contract_execution_rate: '0.920000',
      actual_receipt_today: '650025.00',
      actual_payment_today: '580080.00',
      inventory_turnover_30d: '1.286500',
      threshold_alert_count: 5,
      message: 'ok',
    })
    fetchBoardTasksMock.mockResolvedValue({
      metric_version: 'v1',
      snapshot_time: '2026-03-08T10:05:00+08:00',
      sla_status: '正常',
      pending_supplement_count: 2,
      validation_failed_count: 1,
      qty_done_not_closed_count: 1,
      fulfillment_stagnant_count: 2,
      pending_supplement_items: [],
      validation_failed_items: [],
      qty_done_not_closed_items: [],
      fulfillment_stagnant_items: [],
      message: 'ok',
    })

    const component = await import('./OverviewView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchDashboardSummaryMock).toHaveBeenCalledTimes(1)
    expect(fetchBoardTasksMock).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('合同执行率')
    expect(wrapper.text()).toContain('92.00%')
    expect(wrapper.text()).toContain('¥650,025.00')
    expect(wrapper.text()).toContain('履约滞留')
    expect(wrapper.text()).toContain('2 项')
  }, 10000)

  it('仪表盘加载失败时展示错误提示', async () => {
    fetchDashboardSummaryMock.mockRejectedValue(new Error('仪表盘接口异常'))
    fetchBoardTasksMock.mockResolvedValue({
      metric_version: 'v1',
      snapshot_time: '2026-03-08T10:05:00+08:00',
      sla_status: '正常',
      pending_supplement_count: 0,
      validation_failed_count: 0,
      qty_done_not_closed_count: 0,
      fulfillment_stagnant_count: 0,
      pending_supplement_items: [],
      validation_failed_items: [],
      qty_done_not_closed_items: [],
      fulfillment_stagnant_items: [],
      message: 'ok',
    })

    const component = await import('./OverviewView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()
    const { useReportStore } = await import('@/stores/report')
    const store = useReportStore()

    expect(store.dashboardError).toBe('仪表盘接口异常')
    expect(store.dashboard).toBeNull()
  }, 10000)
})
