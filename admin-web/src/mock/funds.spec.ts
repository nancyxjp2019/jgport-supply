import { describe, expect, it } from 'vitest'

import {
  confirmDemoPaymentDoc,
  confirmDemoReceiptDoc,
  createDemoPaymentSupplement,
  getDemoPaymentDocDetail,
  listDemoPaymentDocs,
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
})
