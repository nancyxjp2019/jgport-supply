import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const pushMock = vi.fn()
let currentRoleCode = 'finance'
const createSummaryReportRecomputeTaskMock = vi.fn().mockResolvedValue({
  task: {
    id: 1201,
    task_name: '汇总报表口径重算',
    status: '已完成',
    metric_version: 'v1',
    report_codes: ['dashboard_summary'],
    reason: '测试创建',
    requested_by: 'tester',
    requested_role_code: 'finance',
    requested_company_id: 'demo-company',
    retry_count: 0,
    error_message: null,
    result_payload: {},
    finished_at: null,
    created_at: '2026-03-08T10:00:00+08:00',
    updated_at: '2026-03-08T10:00:00+08:00',
  },
  message: 'ok',
})
const fetchSummaryReportRecomputeTasksMock = vi.fn().mockResolvedValue({
  items: [
    {
      id: 1202,
      task_name: '汇总报表口径重算',
      status: '已失败',
      metric_version: 'v1',
      report_codes: ['light_overview'],
      reason: '测试失败任务',
      requested_by: 'tester',
      requested_role_code: 'finance',
      requested_company_id: 'demo-company',
      retry_count: 1,
      error_message: '失败',
      result_payload: {},
      finished_at: '2026-03-08T11:00:00+08:00',
      created_at: '2026-03-08T10:30:00+08:00',
      updated_at: '2026-03-08T11:00:00+08:00',
    },
  ],
  message: 'ok',
})
const retrySummaryReportRecomputeTaskMock = vi.fn().mockResolvedValue({
  task: {
    id: 1202,
    task_name: '汇总报表口径重算',
    status: '已完成',
    metric_version: 'v1',
    report_codes: ['light_overview'],
    reason: '测试失败任务',
    requested_by: 'tester',
    requested_role_code: 'finance',
    requested_company_id: 'demo-company',
    retry_count: 2,
    error_message: null,
    result_payload: {},
    finished_at: '2026-03-08T11:05:00+08:00',
    created_at: '2026-03-08T10:30:00+08:00',
    updated_at: '2026-03-08T11:05:00+08:00',
  },
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
    useRouter: () => ({ push: pushMock }),
  }
})

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      warning: vi.fn(),
      success: vi.fn(),
      error: vi.fn(),
    },
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    session: { roleCode: currentRoleCode },
  }),
}))

vi.mock('@/api/reports', () => ({
  createSummaryReportRecomputeTask: createSummaryReportRecomputeTaskMock,
  fetchSummaryReportRecomputeTasks: fetchSummaryReportRecomputeTasksMock,
  retrySummaryReportRecomputeTask: retrySummaryReportRecomputeTaskMock,
}))

describe('ReportRecomputeTasksView', () => {
  it('支持创建汇总重算任务', async () => {
    currentRoleCode = 'finance'
    const component = await import('./ReportRecomputeTasksView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).reason = '修正履约口径后补刷快照'
    ;(wrapper.vm as any).selectedReportCodes = ['dashboard_summary', 'board_tasks']
    await (wrapper.vm as any).handleCreateTask()

    expect(createSummaryReportRecomputeTaskMock).toHaveBeenCalledWith({
      metric_version: 'v1',
      report_codes: ['dashboard_summary', 'board_tasks'],
      reason: '修正履约口径后补刷快照',
    })
  }, 10000)

  it('支持重试失败的汇总重算任务', async () => {
    currentRoleCode = 'finance'
    const component = await import('./ReportRecomputeTasksView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    await (wrapper.vm as any).handleRetry(1202)

    expect(retrySummaryReportRecomputeTaskMock).toHaveBeenCalledWith(1202)
  }, 10000)

  it('运营角色可只读查看历史但不可创建或重试', async () => {
    currentRoleCode = 'operations'
    const component = await import('./ReportRecomputeTasksView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchSummaryReportRecomputeTasksMock).toHaveBeenCalled()
    expect(wrapper.html()).not.toContain('创建重算任务')
    expect(wrapper.html()).toContain('重算任务历史')
    expect((wrapper.vm as any).canManageRecomputeTasks).toBe(false)
  }, 10000)
})
