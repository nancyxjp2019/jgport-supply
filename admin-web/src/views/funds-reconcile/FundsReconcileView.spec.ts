import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const routeState = reactive({
  fullPath: '/funds-reconcile?docType=payment&refundStatus=待审核&limit=260',
  query: {
    docType: 'payment',
    refundStatus: '待审核',
    limit: '260',
    source: 'reports-multi-dim',
    drillGroup: 'refund_status',
    drillValue: '待审核',
  },
})

const fetchPaymentDocsMock = vi.fn().mockResolvedValue({
  items: [
    {
      id: 2,
      doc_no: 'PAY-001',
      doc_type: 'NORMAL',
      contract_id: 102,
      purchase_order_id: 202,
      amount_actual: '200.00',
      status: '已确认',
      voucher_required: true,
      voucher_exempt_reason: null,
      refund_status: '待审核',
      refund_amount: '50.00',
      confirmed_at: '2026-03-08T10:00:00+08:00',
      created_at: '2026-03-08T09:00:00+08:00',
    },
  ],
  total: 1,
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
    useRoute: () => routeState,
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    session: { roleCode: 'finance' },
  }),
}))

vi.mock('@/api/funds', () => ({
  fetchPaymentDocs: fetchPaymentDocsMock,
  fetchReceiptDocs: vi.fn().mockResolvedValue({ items: [], total: 0, message: 'ok' }),
  fetchPaymentDocDetail: vi.fn().mockResolvedValue({
    id: 2,
    doc_no: 'PAY-001',
    doc_type: 'NORMAL',
    contract_id: 102,
    purchase_order_id: 202,
    amount_actual: '200.00',
    status: '已确认',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '待审核',
    refund_amount: '50.00',
    confirmed_at: '2026-03-08T10:00:00+08:00',
    created_at: '2026-03-08T09:00:00+08:00',
    voucher_file_paths: [],
    message: 'ok',
  }),
  fetchReceiptDocDetail: vi.fn().mockResolvedValue({ message: 'ok', voucher_file_paths: [] }),
  requestPaymentRefund: vi.fn(),
  requestReceiptRefund: vi.fn(),
  approvePaymentRefund: vi.fn(),
  approveReceiptRefund: vi.fn(),
  rejectPaymentRefund: vi.fn(),
  rejectReceiptRefund: vi.fn(),
  writeoffPaymentDoc: vi.fn(),
  writeoffReceiptDoc: vi.fn(),
}))

describe('FundsReconcileView', () => {
  it('可承接退款状态钻取 query 并自动回填筛选后加载列表', async () => {
    const component = await import('./FundsReconcileView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchPaymentDocsMock).toHaveBeenCalledWith({
      status: undefined,
      refund_status: '待审核',
      limit: 260,
    })
    expect((wrapper.vm as any).docType).toBe('payment')
    expect((wrapper.vm as any).refundStatusFilter).toBe('待审核')
    expect((wrapper.vm as any).listLimit).toBe(260)
  }, 10000)
})
