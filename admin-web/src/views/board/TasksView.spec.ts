import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

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
  fetchDashboardSummary: vi.fn(),
}))

describe('TasksView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchBoardTasksMock.mockReset()
  })

  it('挂载后加载业务看板并展示四类告警与待办列表', async () => {
    fetchBoardTasksMock.mockResolvedValue({
      metric_version: 'v1',
      snapshot_time: '2026-03-08T10:05:00+08:00',
      sla_status: '正常',
      pending_supplement_count: 2,
      validation_failed_count: 1,
      qty_done_not_closed_count: 1,
      fulfillment_stagnant_count: 1,
      pending_supplement_items: [
        {
          biz_type: 'receipt_doc',
          biz_id: 101,
          title: '收款单 REC-101 待补录金额',
          status: '待补录金额',
          contract_id: 301,
          contract_no: 'XS-202603-001',
          related_order_id: 501,
          created_at: '2026-03-08T09:20:00+08:00',
        },
      ],
      validation_failed_items: [
        {
          biz_type: 'inbound_doc',
          biz_id: 201,
          title: '入库单 INB-201 校验失败',
          status: '校验失败',
          contract_id: 302,
          contract_no: 'CG-202603-001',
          related_order_id: null,
          created_at: '2026-03-08T09:30:00+08:00',
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
          created_at: '2026-03-08T09:40:00+08:00',
        },
      ],
      fulfillment_stagnant_items: [
        {
          biz_type: 'contract',
          biz_id: 401,
          title: '合同 XS-202603-010 履约滞留',
          status: '生效中',
          contract_id: 401,
          contract_no: 'XS-202603-010',
          related_order_id: null,
          created_at: '2026-03-04T09:30:00+08:00',
          last_effect_at: '2026-03-04T09:30:00+08:00',
          days_without_effect: 4,
          scan_type: '履约滞留',
          scan_date: '2026-03-08',
        },
      ],
      message: 'ok',
    })

    const component = await import('./TasksView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()
    const { useReportStore } = await import('@/stores/report')
    const store = useReportStore()

    expect(fetchBoardTasksMock).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('待补录金额')
    expect(wrapper.text()).toContain('校验失败')
    expect(wrapper.text()).toContain('数量履约完成未关闭')
    expect(wrapper.text()).toContain('履约滞留')
    expect(store.board?.pending_supplement_items[0]?.title).toBe('收款单 REC-101 待补录金额')
    expect(store.board?.fulfillment_stagnant_items[0]?.days_without_effect).toBe(4)
  }, 10000)

  it('接口失败时展示错误提示与空态', async () => {
    fetchBoardTasksMock.mockRejectedValue(new Error('业务看板接口异常'))

    const component = await import('./TasksView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()
    const { useReportStore } = await import('@/stores/report')
    const store = useReportStore()

    expect(store.boardError).toBe('业务看板接口异常')
    expect(store.board).toBeNull()
  }, 10000)
})
