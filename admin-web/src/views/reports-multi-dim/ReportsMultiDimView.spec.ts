import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const pushMock = vi.fn()
const fetchAdminMultiDimReportMock = vi.fn().mockResolvedValue({
  metric_version: 'v1',
  snapshot_time: '2026-03-08T10:00:00+08:00',
  sla_status: 'T+0',
  group_by: 'contract_direction',
  filters: {},
  total_receipt_net_amount: '0.00',
  total_payment_net_amount: '0.00',
  total_net_cashflow: '0.00',
  rows: [],
  message: 'ok',
})

const mountOptions = {
  global: {
    directives: {
      loading: () => undefined,
    },
  },
}

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRouter: () => ({ push: pushMock }),
  }
})

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      warning: vi.fn(),
      success: vi.fn(),
      error: vi.fn(),
    },
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    session: { roleCode: 'admin' },
  }),
}))

vi.mock('@/api/reports', () => ({
  createAdminMultiDimExportTask: vi.fn(),
  fetchAdminMultiDimReport: fetchAdminMultiDimReportMock,
}))

describe('ReportsMultiDimView', () => {
  it('可从 doc_status 汇总行钻取到资金处理台', async () => {
    const component = await import('./ReportsMultiDimView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).groupBy = 'doc_status'
    await (wrapper.vm as any).handleDrill(
      {
        dimension: 'doc_status',
        dimension_value: '已确认',
        receipt_net_amount: '5000.00',
        payment_net_amount: '3000.00',
        net_cashflow: '2000.00',
        receipt_doc_count: 12,
        payment_doc_count: 8,
        pending_supplement_count: 0,
        refund_pending_review_count: 0,
      },
      'receipt',
    )

    expect(pushMock).toHaveBeenCalledWith({
      path: '/funds',
      query: {
        docType: 'receipt',
        status: '已确认',
        limit: '200',
        source: 'reports-multi-dim',
        drillGroup: 'doc_status',
        drillValue: '已确认',
      },
    })
  })

  it('合同方向维度不触发真实钻取跳转', async () => {
    pushMock.mockClear()
    const component = await import('./ReportsMultiDimView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).groupBy = 'contract_direction'
    await (wrapper.vm as any).handleDrill(
      {
        dimension: 'contract_direction',
        dimension_value: '销售',
        receipt_net_amount: '5000.00',
        payment_net_amount: '3000.00',
        net_cashflow: '2000.00',
        receipt_doc_count: 12,
        payment_doc_count: 8,
        pending_supplement_count: 0,
        refund_pending_review_count: 0,
      },
      'payment',
    )

    expect(pushMock).not.toHaveBeenCalled()
  })

  it('可从 refund_status 汇总行钻取到退款核销台', async () => {
    pushMock.mockClear()
    const component = await import('./ReportsMultiDimView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).groupBy = 'refund_status'
    await (wrapper.vm as any).handleDrill(
      {
        dimension: 'refund_status',
        dimension_value: '待审核',
        receipt_net_amount: '5000.00',
        payment_net_amount: '3000.00',
        net_cashflow: '2000.00',
        receipt_doc_count: 12,
        payment_doc_count: 8,
        pending_supplement_count: 0,
        refund_pending_review_count: 3,
      },
      'payment',
    )

    expect(pushMock).toHaveBeenCalledWith({
      path: '/funds-reconcile',
      query: {
        docType: 'payment',
        refundStatus: '待审核',
        limit: '200',
        source: 'reports-multi-dim',
        drillGroup: 'refund_status',
        drillValue: '待审核',
      },
    })
  })
})
