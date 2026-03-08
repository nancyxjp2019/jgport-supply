import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const routeState = reactive({
  fullPath: '/funds-reconcile?docType=payment&limit=220',
  query: {
    docType: 'payment',
    limit: '220',
  },
})

const authState = reactive({
  session: { roleCode: 'finance' },
})

const paymentListResponse = {
  items: [
    {
      id: 9101,
      doc_no: 'PAY-REC-9101',
      doc_type: 'NORMAL',
      contract_id: 5201,
      purchase_order_id: 9301,
      amount_actual: '3200.55',
      status: '已确认',
      voucher_required: true,
      voucher_exempt_reason: null,
      refund_status: '未退款',
      refund_amount: '0.00',
      confirmed_at: '2026-03-08T11:00:00+08:00',
      created_at: '2026-03-08T09:00:00+08:00',
    },
  ],
  total: 1,
  message: 'ok',
}

const paymentDetail = {
  ...paymentListResponse.items[0],
  voucher_file_paths: ['CODEX-TEST-/refund-payment-001.png'],
  message: 'ok',
}

const fetchPaymentDocsMock = vi.fn().mockResolvedValue(paymentListResponse)
const fetchPaymentDocDetailMock = vi.fn().mockResolvedValue(paymentDetail)
const requestPaymentRefundMock = vi.fn().mockResolvedValue({
  ...paymentDetail,
  refund_status: '待审核',
  refund_amount: '1000.00',
  message: '退款申请成功',
})
const approvePaymentRefundMock = vi.fn().mockResolvedValue({
  ...paymentDetail,
  refund_status: '部分退款',
  refund_amount: '1000.00',
  message: '退款审核通过',
})
const rejectPaymentRefundMock = vi.fn().mockResolvedValue({
  ...paymentDetail,
  refund_status: '驳回',
  refund_amount: '0.00',
  message: '退款驳回成功',
})
const writeoffPaymentDocMock = vi.fn().mockResolvedValue({
  ...paymentDetail,
  status: '已核销',
  message: '核销成功',
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
  requestPaymentRefund: requestPaymentRefundMock,
  requestReceiptRefund: vi.fn(),
  approvePaymentRefund: approvePaymentRefundMock,
  approveReceiptRefund: vi.fn(),
  rejectPaymentRefund: rejectPaymentRefundMock,
  rejectReceiptRefund: vi.fn(),
  writeoffPaymentDoc: writeoffPaymentDocMock,
  writeoffReceiptDoc: vi.fn(),
}))

describe('FundsReconcileView actions', () => {
  it('财务可发起付款退款审核并刷新列表', async () => {
    authState.session.roleCode = 'finance'
    requestPaymentRefundMock.mockClear()
    fetchPaymentDocsMock.mockClear()

    const component = await import('./FundsReconcileView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).refundRequestDialog.refundAmount = 1000
    ;(wrapper.vm as any).refundRequestDialog.reason = '退款申请说明'
    await (wrapper.vm as any).submitRefundRequest()

    expect(requestPaymentRefundMock).toHaveBeenCalledWith(9101, {
      refund_amount: 1000,
      reason: '退款申请说明',
    })
    expect(fetchPaymentDocsMock).toHaveBeenLastCalledWith({
      status: undefined,
      refund_status: undefined,
      limit: 220,
    })
  }, 10000)

  it('财务可完成退款驳回、审核通过与核销链路', async () => {
    authState.session.roleCode = 'finance'
    rejectPaymentRefundMock.mockClear()
    approvePaymentRefundMock.mockClear()
    writeoffPaymentDocMock.mockClear()

    const component = await import('./FundsReconcileView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).selectedDoc = { ...paymentDetail, refund_status: '待审核', status: '已确认' }
    ;(wrapper.vm as any).refundDecisionDialog.mode = 'reject'
    ;(wrapper.vm as any).refundDecisionDialog.reason = '退款驳回说明'
    await (wrapper.vm as any).submitRefundDecision()

    ;(wrapper.vm as any).selectedDoc = { ...paymentDetail, refund_status: '待审核', status: '已确认' }
    ;(wrapper.vm as any).refundDecisionDialog.mode = 'approve'
    ;(wrapper.vm as any).refundDecisionDialog.reason = '退款审核通过说明'
    await (wrapper.vm as any).submitRefundDecision()

    ;(wrapper.vm as any).selectedDoc = { ...paymentDetail, refund_status: '部分退款', status: '已确认' }
    ;(wrapper.vm as any).writeoffDialog.comment = '执行核销说明'
    await (wrapper.vm as any).submitWriteoff()

    expect(rejectPaymentRefundMock).toHaveBeenCalledWith(9101, { reason: '退款驳回说明' })
    expect(approvePaymentRefundMock).toHaveBeenCalledWith(9101, { reason: '退款审核通过说明' })
    expect(writeoffPaymentDocMock).toHaveBeenCalledWith(9101, { comment: '执行核销说明' })
  }, 10000)

  it('运营角色只能回看，不能发起退款审核或核销', async () => {
    authState.session.roleCode = 'operations'
    messageWarning.mockClear()
    requestPaymentRefundMock.mockClear()
    approvePaymentRefundMock.mockClear()
    writeoffPaymentDocMock.mockClear()

    const component = await import('./FundsReconcileView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).selectedDoc = { ...paymentDetail, refund_status: '待审核', status: '已确认' }
    ;(wrapper.vm as any).openRefundRequestDialog()
    ;(wrapper.vm as any).openRefundDecisionDialog('approve')
    ;(wrapper.vm as any).openWriteoffDialog()

    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行退款审核动作')
    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行核销动作')
    expect(requestPaymentRefundMock).not.toHaveBeenCalled()
    expect(approvePaymentRefundMock).not.toHaveBeenCalled()
    expect(writeoffPaymentDocMock).not.toHaveBeenCalled()
  }, 10000)
})
