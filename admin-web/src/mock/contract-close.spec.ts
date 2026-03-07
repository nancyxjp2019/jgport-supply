import { describe, expect, it } from 'vitest'

import {
  getDemoContractDetail,
  listDemoContracts,
  manualCloseDemoContract,
} from '@/mock/contract-close'

describe('合同关闭差异台演示数据', () => {
  it('可按关闭类型筛选自动关闭合同', () => {
    const response = listDemoContracts({ close_type: 'AUTO' })
    expect(response.total).toBeGreaterThan(0)
    expect(response.items.every((item) => item.close_type === 'AUTO')).toBe(true)
  })

  it('可查询合同详情', () => {
    const detail = getDemoContractDetail(5301)
    expect(detail.contract_no).toBe('XS-DEMO-5301')
    expect(detail.status).toBe('已关闭')
  })

  it('数量履约完成合同可执行手工关闭', () => {
    const updated = manualCloseDemoContract(5302, {
      reason: 'AUTO-TEST-金额未闭环，执行手工关闭',
      confirm_token: 'MANUAL_CLOSE',
    })
    expect(updated.status).toBe('手工关闭')
    expect(updated.close_type).toBe('MANUAL')
    expect(updated.manual_close_diff_qty_json?.length).toBeGreaterThan(0)
  })
})
