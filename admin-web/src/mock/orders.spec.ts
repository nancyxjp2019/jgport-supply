import { describe, expect, it } from 'vitest'

import {
  approveDemoSalesOrderByFinance,
  approveDemoSalesOrderByOps,
  getDemoSalesOrderDetail,
  listDemoSalesOrders,
} from '@/mock/orders'

describe('运营订单处理台演示数据', () => {
  it('可按状态筛选待运营审批订单', () => {
    const response = listDemoSalesOrders('待运营审批')
    expect(response.total).toBeGreaterThan(0)
    expect(response.items.every((item) => item.status === '待运营审批')).toBe(true)
  })

  it('运营审批通过后订单进入待财务审批', () => {
    const updated = approveDemoSalesOrderByOps(6101, true, 'CODEX-TEST-运营审批通过')
    expect(updated.status).toBe('待财务审批')
    expect(updated.ops_comment).toBe('CODEX-TEST-运营审批通过')
  })

  it('财务审批通过后订单生成采购订单号', () => {
    const updated = approveDemoSalesOrderByFinance(6102, {
      result: true,
      purchase_contract_id: 8901,
      actual_receipt_amount: 12000.34,
      actual_pay_amount: 11800.12,
      comment: 'CODEX-TEST-财务审批通过',
    })
    expect(updated.status).toBe('已衍生采购订单')
    expect(updated.purchase_order_id).toBeTruthy()
    expect(updated.generated_task_count).toBe(2)
    const detail = getDemoSalesOrderDetail(6102)
    expect(detail.status).toBe('已衍生采购订单')
  })
})
