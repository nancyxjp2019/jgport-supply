import { describe, expect, it } from 'vitest'

import {
  getDemoInboundDocDetail,
  getDemoOutboundDocDetail,
  listDemoInboundDocs,
  listDemoOutboundDocs,
} from '@/mock/inventory'

describe('库存执行跟踪台演示数据', () => {
  it('可按状态筛选校验失败入库单', () => {
    const response = listDemoInboundDocs({ status: '校验失败' })
    expect(response.total).toBeGreaterThan(0)
    expect(response.items.every((item) => item.status === '校验失败')).toBe(true)
  })

  it('可按来源类型筛选手工出库单', () => {
    const response = listDemoOutboundDocs({ source_type: 'MANUAL' })
    expect(response.total).toBeGreaterThan(0)
    expect(response.items.every((item) => item.source_type === 'MANUAL')).toBe(true)
  })

  it('可查询入库单与出库单详情', () => {
    const inbound = getDemoInboundDocDetail(9101)
    expect(inbound.doc_no).toBe('INB-DEMO-9101')

    const outbound = getDemoOutboundDocDetail(9201)
    expect(outbound.doc_no).toBe('OUT-DEMO-9201')
  })
})
