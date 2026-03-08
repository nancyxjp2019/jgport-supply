import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const pushMock = vi.fn()
let currentRoleCode = 'finance'

const fetchAdminMultiDimExportTasksMock = vi.fn()
const downloadAdminMultiDimExportTaskMock = vi.fn()
const retryAdminMultiDimExportTaskMock = vi.fn()
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
    useRouter: () => ({ push: pushMock }),
  }
})

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: messageSuccess,
      error: messageError,
      warning: vi.fn(),
    },
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    session: { roleCode: currentRoleCode },
  }),
}))

vi.mock('@/api/reports', () => ({
  fetchAdminMultiDimExportTasks: fetchAdminMultiDimExportTasksMock,
  downloadAdminMultiDimExportTask: downloadAdminMultiDimExportTaskMock,
  retryAdminMultiDimExportTask: retryAdminMultiDimExportTaskMock,
}))

describe('ReportExportTasksView', () => {
  beforeEach(() => {
    currentRoleCode = 'finance'
    pushMock.mockReset()
    fetchAdminMultiDimExportTasksMock.mockReset()
    downloadAdminMultiDimExportTaskMock.mockReset()
    retryAdminMultiDimExportTaskMock.mockReset()
    messageSuccess.mockReset()
    messageError.mockReset()

    fetchAdminMultiDimExportTasksMock.mockResolvedValue({
      items: [
        {
          id: 2101,
          report_code: 'admin_multi_dim',
          report_name: '多维报表',
          status: '已完成',
          export_format: 'csv',
          metric_version: 'v1',
          filters: {
            group_by: 'refund_status',
            contract_direction: 'purchase',
            doc_status: null,
            refund_status: '待审核',
            date_from: '2026-03-08',
            date_to: '2026-03-08',
          },
          file_name: 'report-2101.csv',
          requested_by: 'tester',
          requested_role_code: 'finance',
          requested_company_id: 'demo-company',
          retry_count: 0,
          download_count: 1,
          error_message: null,
          finished_at: '2026-03-08T11:00:00+08:00',
          created_at: '2026-03-08T10:30:00+08:00',
          updated_at: '2026-03-08T11:00:00+08:00',
        },
        {
          id: 2102,
          report_code: 'admin_multi_dim',
          report_name: '多维报表',
          status: '已失败',
          export_format: 'csv',
          metric_version: 'v1',
          filters: {
            group_by: 'doc_status',
            contract_direction: 'sales',
            doc_status: '待补录金额',
            refund_status: null,
            date_from: '2026-03-08',
            date_to: '2026-03-08',
          },
          file_name: null,
          requested_by: 'tester',
          requested_role_code: 'finance',
          requested_company_id: 'demo-company',
          retry_count: 1,
          download_count: 0,
          error_message: '导出失败',
          finished_at: '2026-03-08T11:10:00+08:00',
          created_at: '2026-03-08T10:35:00+08:00',
          updated_at: '2026-03-08T11:10:00+08:00',
        },
      ],
      message: 'ok',
    })
    downloadAdminMultiDimExportTaskMock.mockResolvedValue(new Blob(['csv'], { type: 'text/csv' }))
    retryAdminMultiDimExportTaskMock.mockResolvedValue({
      task: {
        id: 2102,
      },
      message: 'ok',
    })
  })

  it('财务角色可加载任务中心并看到完成与失败任务', async () => {
    const component = await import('./ReportExportTasksView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    const createObjectURLMock = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:codex-export')
    const revokeObjectURLMock = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
    const clickMock = vi.fn()
    const originalCreateElement = document.createElement.bind(document)
    const createElementMock = vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return {
          click: clickMock,
          href: '',
          download: '',
        } as unknown as HTMLAnchorElement
      }
      return originalCreateElement(tagName)
    })

    expect(fetchAdminMultiDimExportTasksMock).toHaveBeenCalledWith({ status: undefined, limit: 30 })
    expect(wrapper.text()).toContain('任务总数')
    expect(wrapper.text()).toContain('共 2 条')

    await (wrapper.vm as any).handleDownload(2101, 'report-2101.csv')
    await flushPromises()
    expect(downloadAdminMultiDimExportTaskMock).toHaveBeenCalledWith(2101)
    expect(clickMock).toHaveBeenCalled()
    expect(messageSuccess).toHaveBeenCalledWith('导出文件下载已开始')

    await (wrapper.vm as any).handleRetry(2102)
    await flushPromises()
    expect(retryAdminMultiDimExportTaskMock).toHaveBeenCalledWith(2102)
    expect(messageSuccess).toHaveBeenCalledWith('导出任务已重新发起，请稍后刷新结果')

    createObjectURLMock.mockRestore()
    revokeObjectURLMock.mockRestore()
    createElementMock.mockRestore()
  }, 10000)

  it('运营角色仅看到只读空态，不请求任务中心接口', async () => {
    currentRoleCode = 'operations'

    const component = await import('./ReportExportTasksView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchAdminMultiDimExportTasksMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('导出任务中心仅对财务与管理员开放')
  }, 10000)
})
