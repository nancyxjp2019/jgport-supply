import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const routeState = reactive({
  fullPath: '/funds?docType=receipt&status=已确认&limit=120',
  query: {
    docType: 'receipt',
    status: '已确认',
    limit: '120',
    source: 'reports-multi-dim',
    drillGroup: 'doc_status',
    drillValue: '已确认',
  },
})

const fetchPaymentDocsMock = vi.fn().mockResolvedValue({ items: [], total: 0, message: 'ok' })
const fetchReceiptDocsMock = vi.fn().mockResolvedValue({
  items: [
    {
      id: 1,
      doc_no: 'REC-001',
      doc_type: 'NORMAL',
      contract_id: 101,
      sales_order_id: 201,
      amount_actual: '100.00',
      status: '已确认',
      voucher_required: true,
      voucher_exempt_reason: null,
      refund_status: '未退款',
      refund_amount: '0.00',
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
  fetchReceiptDocs: fetchReceiptDocsMock,
  fetchPaymentDocDetail: vi.fn().mockResolvedValue({ message: 'ok', voucher_file_paths: [] }),
  fetchReceiptDocDetail: vi.fn().mockResolvedValue({
    id: 1,
    doc_no: 'REC-001',
    doc_type: 'NORMAL',
    contract_id: 101,
    sales_order_id: 201,
    amount_actual: '100.00',
    status: '已确认',
    voucher_required: true,
    voucher_exempt_reason: null,
    refund_status: '未退款',
    refund_amount: '0.00',
    confirmed_at: '2026-03-08T10:00:00+08:00',
    created_at: '2026-03-08T09:00:00+08:00',
    voucher_file_paths: [],
    message: 'ok',
  }),
  createPaymentSupplement: vi.fn(),
  createReceiptSupplement: vi.fn(),
  confirmPaymentDoc: vi.fn(),
  confirmReceiptDoc: vi.fn(),
}))

describe('FundsView', () => {
  it('可承接钻取 query 并自动回填筛选后加载列表', async () => {
    const component = await import('./FundsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchReceiptDocsMock).toHaveBeenCalledWith({ status: '已确认', limit: 120 })
    expect((wrapper.vm as any).docType).toBe('receipt')
    expect((wrapper.vm as any).statusFilter).toBe('已确认')
    expect((wrapper.vm as any).listLimit).toBe(120)
  })
})
