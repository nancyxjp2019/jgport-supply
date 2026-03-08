import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const routeState = reactive({
  fullPath: '/funds?docType=payment&status=草稿&limit=120',
  query: {
    docType: 'payment',
    status: '草稿',
    limit: '120',
  },
})

const authState = reactive({
  session: { roleCode: 'finance' },
})

const paymentListResponse = {
  items: [
    {
      id: 8101,
      doc_no: 'PAY-CHAIN-8101',
      doc_type: 'NORMAL',
      contract_id: 5201,
      purchase_order_id: 9101,
      amount_actual: '0.00',
      status: '草稿',
      voucher_required: true,
      voucher_exempt_reason: null,
      refund_status: '未退款',
      refund_amount: '0.00',
      confirmed_at: null,
      created_at: '2026-03-08T09:00:00+08:00',
    },
  ],
  total: 1,
  message: 'ok',
}

const paymentDetail = {
  ...paymentListResponse.items[0],
  voucher_file_paths: [],
  message: 'ok',
}

const fetchPaymentDocsMock = vi.fn().mockResolvedValue(paymentListResponse)
const fetchPaymentDocDetailMock = vi.fn().mockResolvedValue(paymentDetail)
const createPaymentSupplementMock = vi.fn().mockResolvedValue({
  ...paymentDetail,
  id: 8901,
  doc_no: 'PAY-CHAIN-8901',
  contract_id: 5202,
  purchase_order_id: 9102,
  amount_actual: '8888.88',
  message: '付款单补录成功',
})
const confirmPaymentDocMock = vi.fn().mockResolvedValue({
  ...paymentDetail,
  amount_actual: '3200.55',
  status: '已确认',
  voucher_file_paths: ['CODEX-TEST-/pay-a.png', 'CODEX-TEST-/pay-b.png'],
  message: '付款单确认成功',
})

const messageWarning = vi.fn()
const messageSuccess = vi.fn()
const messageError = vi.fn()

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

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      warning: messageWarning,
      success: messageSuccess,
      error: messageError,
    },
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authState,
}))

vi.mock('@/api/funds', () => ({
  fetchPaymentDocs: fetchPaymentDocsMock,
  fetchReceiptDocs: vi.fn().mockResolvedValue({ items: [], total: 0, message: 'ok' }),
  fetchPaymentDocDetail: fetchPaymentDocDetailMock,
  fetchReceiptDocDetail: vi.fn().mockResolvedValue({ message: 'ok', voucher_file_paths: [] }),
  createPaymentSupplement: createPaymentSupplementMock,
  createReceiptSupplement: vi.fn(),
  confirmPaymentDoc: confirmPaymentDocMock,
  confirmReceiptDoc: vi.fn(),
}))

describe('FundsView actions', () => {
  it('财务可补录付款单并刷新列表', async () => {
    authState.session.roleCode = 'finance'
    createPaymentSupplementMock.mockClear()
    fetchPaymentDocsMock.mockClear()

    const component = await import('./FundsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).openSupplementDialog()
    ;(wrapper.vm as any).supplementDialog.contractId = 5202
    ;(wrapper.vm as any).supplementDialog.relatedOrderId = 9102
    ;(wrapper.vm as any).supplementDialog.amountActual = 8888.88
    await (wrapper.vm as any).submitSupplement()

    expect(createPaymentSupplementMock).toHaveBeenCalledWith({
      contract_id: 5202,
      purchase_order_id: 9102,
      amount_actual: 8888.88,
    })
    expect(fetchPaymentDocsMock).toHaveBeenLastCalledWith({ status: '草稿', limit: 120 })
  }, 10000)

  it('财务可确认付款单并去重凭证路径后刷新列表', async () => {
    authState.session.roleCode = 'finance'
    confirmPaymentDocMock.mockClear()
    fetchPaymentDocsMock.mockClear()

    const component = await import('./FundsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).confirmDialog.amountActual = 3200.55
    ;(wrapper.vm as any).confirmDialog.voucherLines = 'CODEX-TEST-/pay-a.png\nCODEX-TEST-/pay-b.png\nCODEX-TEST-/pay-a.png'
    await (wrapper.vm as any).submitConfirm()

    expect(confirmPaymentDocMock).toHaveBeenCalledWith(8101, {
      amount_actual: 3200.55,
      voucher_files: ['CODEX-TEST-/pay-a.png', 'CODEX-TEST-/pay-b.png'],
    })
    expect(fetchPaymentDocsMock).toHaveBeenLastCalledWith({ status: '草稿', limit: 120 })
  }, 10000)

  it('非0金额确认缺少凭证路径时会阻断提交', async () => {
    authState.session.roleCode = 'finance'
    messageWarning.mockClear()
    confirmPaymentDocMock.mockClear()

    const component = await import('./FundsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).confirmDialog.amountActual = 1200
    ;(wrapper.vm as any).confirmDialog.voucherLines = ''
    await (wrapper.vm as any).submitConfirm()

    expect(messageWarning).toHaveBeenCalledWith('非0金额确认必须至少填写一条凭证路径')
    expect(confirmPaymentDocMock).not.toHaveBeenCalled()
  }, 10000)

  it('运营角色只能回看，不能补录或确认资金单据', async () => {
    authState.session.roleCode = 'operations'
    messageWarning.mockClear()
    createPaymentSupplementMock.mockClear()
    confirmPaymentDocMock.mockClear()

    const component = await import('./FundsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).openSupplementDialog()
    ;(wrapper.vm as any).openConfirmDialog()

    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行资金补录动作')
    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行资金确认动作')
    expect(createPaymentSupplementMock).not.toHaveBeenCalled()
    expect(confirmPaymentDocMock).not.toHaveBeenCalled()
  }, 10000)
})
