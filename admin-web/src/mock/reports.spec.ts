import { describe, expect, it } from 'vitest'

import {
  buildDemoAdminMultiDimReportCsv,
  createDemoAdminMultiDimExportTask,
  downloadDemoAdminMultiDimExportTask,
  getDemoAdminMultiDimExportTasks,
  getDemoAdminMultiDimReport,
  retryDemoAdminMultiDimExportTask,
} from '@/mock/reports'

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

  it('支持创建并查询导出任务历史', () => {
    const created = createDemoAdminMultiDimExportTask({
      group_by: 'contract_direction',
      contract_direction: 'purchase',
    })
    expect(created.message).toBe('导出任务已创建，正在后台生成文件')
    expect(created.task.status).toBe('已完成')

    const list = getDemoAdminMultiDimExportTasks({ status: '已完成' })
    expect(list.items.some((item) => item.id === created.task.id)).toBe(true)
  })

  it('支持下载已完成任务并重试失败任务', async () => {
    const list = getDemoAdminMultiDimExportTasks()
    const completedTask = list.items.find((item) => item.status === '已完成')
    const failedTask = list.items.find((item) => item.status === '已失败')
    expect(completedTask).toBeDefined()
    expect(failedTask).toBeDefined()

    const blob = downloadDemoAdminMultiDimExportTask(completedTask!.id)
    await expect(blob.text()).resolves.toContain('维度,维度值,收款净额,付款净额,资金净流入')

    const retried = retryDemoAdminMultiDimExportTask(failedTask!.id)
    expect(retried.task.status).toBe('已完成')
    expect(retried.task.retry_count).toBeGreaterThan(1)
  })
})
