import { describe, expect, it } from 'vitest'

import { buildDemoAdminMultiDimReportCsv, getDemoAdminMultiDimReport } from '@/mock/reports'

describe('多维报表演示数据', () => {
  it('支持按合同方向筛选并返回采购维度汇总', () => {
    const report = getDemoAdminMultiDimReport({
      group_by: 'refund_status',
      contract_direction: 'purchase',
    })
    expect(report.group_by).toBe('refund_status')
    expect(report.rows.length).toBeGreaterThan(0)
    expect(report.rows.some((row) => row.dimension_value === '待审核')).toBe(true)
    expect(Number.parseFloat(report.total_payment_net_amount)).toBeGreaterThan(0)
  })

  it('支持导出CSV文本', () => {
    const csv = buildDemoAdminMultiDimReportCsv({
      group_by: 'contract_direction',
    })
    expect(csv).toContain('维度,维度值,收款净额,付款净额,资金净流入')
    expect(csv).toContain('contract_direction,销售')
    expect(csv).toContain('contract_direction,采购')
  })
})
