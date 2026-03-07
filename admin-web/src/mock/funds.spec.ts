import { describe, expect, it } from 'vitest'

import {
  approveDemoPaymentRefund,
  confirmDemoPaymentDoc,
  confirmDemoReceiptDoc,
  createDemoPaymentSupplement,
  getDemoPaymentDocDetail,
  listDemoPaymentDocs,
  rejectDemoPaymentRefund,
  requestDemoPaymentRefund,
  writeoffDemoPaymentDoc,
} from '@/mock/funds'

describe('财务资金处理台演示数据', () => {
  it('可按状态筛选付款单', () => {
    const response = listDemoPaymentDocs('待补录金额')
    expect(response.total).toBeGreaterThan(0)
    expect(response.items.every((item) => item.status === '待补录金额')).toBe(true)
  })

  it('可补录付款单并在详情中查询到', () => {
    const created = createDemoPaymentSupplement({
      contract_id: 7201,
      purchase_order_id: 9301,
      amount_actual: 12888.66,
    })
    expect(created.status).toBe('草稿')
    expect(created.amount_actual).toBe('12888.66')

    const detail = getDemoPaymentDocDetail(created.id)
    expect(detail.contract_id).toBe(7201)
    expect(detail.purchase_order_id).toBe(9301)
  })

  it('付款单0金额命中规则11可确认，收款单0金额不满足规则14转待补录', () => {
    const payConfirmed = confirmDemoPaymentDoc(8101, {
      amount_actual: 0,
      voucher_files: [],
    })
    expect(payConfirmed.status).toBe('已确认')
    expect(payConfirmed.voucher_exempt_reason).toBe('例外放行（需后补付款单）')

    const receiptBlocked = confirmDemoReceiptDoc(8202, {
      amount_actual: 0,
      voucher_files: [],
    })
    expect(receiptBlocked.status).toBe('待补录金额')
    expect(receiptBlocked.voucher_required).toBe(true)
  })

  it('付款单支持退款待审核、驳回、审核通过与核销', () => {
    const refundRequested = requestDemoPaymentRefund(8103, {
      refund_amount: 10000,
      reason: 'AUTO-TEST-退款申请',
    })
    expect(refundRequested.refund_status).toBe('待审核')

    const refundRejected = rejectDemoPaymentRefund(8103, {
      reason: 'AUTO-TEST-退款驳回',
    })
    expect(refundRejected.refund_status).toBe('驳回')
    expect(refundRejected.refund_amount).toBe('0.00')

    requestDemoPaymentRefund(8103, {
      refund_amount: 50000,
      reason: 'AUTO-TEST-退款复提',
    })
    const refundApproved = approveDemoPaymentRefund(8103, {
      reason: 'AUTO-TEST-退款审核通过',
    })
    expect(refundApproved.refund_status).toBe('已退款')

    const writeoff = writeoffDemoPaymentDoc(8103, {
      comment: 'AUTO-TEST-付款核销',
    })
    expect(writeoff.status).toBe('已核销')
  })
})
