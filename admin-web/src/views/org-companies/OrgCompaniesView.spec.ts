import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const authState = reactive({
  session: { roleCode: 'admin' },
})

const fetchCompaniesMock = vi.fn()
const fetchCompanyDetailMock = vi.fn()
const createCompanyMock = vi.fn()
const updateCompanyMock = vi.fn()
const updateCompanyStatusMock = vi.fn()

const mountOptions = {
  global: {
    directives: {
      loading: () => undefined,
    },
  },
}

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
  useAuthStore: () => authState,
}))

vi.mock('@/api/companies', () => ({
  fetchCompanies: fetchCompaniesMock,
  fetchCompanyDetail: fetchCompanyDetailMock,
  createCompany: createCompanyMock,
  updateCompany: updateCompanyMock,
  updateCompanyStatus: updateCompanyStatusMock,
}))

describe('OrgCompaniesView', () => {
  it('管理员挂载后加载公司列表、运营商列表与详情', async () => {
    authState.session.roleCode = 'admin'
    fetchCompaniesMock.mockReset()
    fetchCompanyDetailMock.mockReset()
    fetchCompaniesMock
      .mockResolvedValueOnce({
        items: [
          {
            company_id: 'AUTO-TEST-OPERATOR-001',
            company_name: '运营商一号',
            company_type: 'operator_company',
            parent_company_id: null,
            parent_company_name: null,
            status: '启用',
            is_active: true,
            remark: null,
            child_company_count: 1,
            created_at: '2026-03-08T08:00:00+08:00',
            updated_at: '2026-03-08T08:00:00+08:00',
          },
        ],
        total: 1,
        message: 'ok',
      })
      .mockResolvedValueOnce({
        items: [
          {
            company_id: 'AUTO-TEST-OPERATOR-001',
            company_name: '运营商一号',
            company_type: 'operator_company',
            parent_company_id: null,
            parent_company_name: null,
            status: '启用',
            is_active: true,
            remark: null,
            child_company_count: 1,
            created_at: '2026-03-08T08:00:00+08:00',
            updated_at: '2026-03-08T08:00:00+08:00',
          },
        ],
        total: 1,
        message: 'ok',
      })
    fetchCompanyDetailMock.mockResolvedValue({
      company_id: 'AUTO-TEST-OPERATOR-001',
      company_name: '运营商一号',
      company_type: 'operator_company',
      parent_company_id: null,
      parent_company_name: null,
      status: '启用',
      is_active: true,
      remark: null,
      child_company_count: 1,
      created_at: '2026-03-08T08:00:00+08:00',
      updated_at: '2026-03-08T08:00:00+08:00',
      created_by: 'admin',
      updated_by: 'admin',
      message: 'ok',
    })

    const component = await import('./OrgCompaniesView.vue')
    shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchCompaniesMock).toHaveBeenNthCalledWith(1, { company_type: undefined, status: undefined })
    expect(fetchCompaniesMock).toHaveBeenNthCalledWith(2, { company_type: 'operator_company', status: '启用' })
    expect(fetchCompanyDetailMock).toHaveBeenCalledWith('AUTO-TEST-OPERATOR-001')
  }, 10000)

  it('管理员可创建公司、编辑公司并变更状态', async () => {
    authState.session.roleCode = 'admin'
    fetchCompaniesMock.mockReset()
    fetchCompanyDetailMock.mockReset()
    createCompanyMock.mockReset()
    updateCompanyMock.mockReset()
    updateCompanyStatusMock.mockReset()
    fetchCompaniesMock
      .mockResolvedValue({
        items: [
          {
            company_id: 'AUTO-TEST-OPERATOR-001',
            company_name: '运营商一号',
            company_type: 'operator_company',
            parent_company_id: null,
            parent_company_name: null,
            status: '启用',
            is_active: true,
            remark: null,
            child_company_count: 0,
            created_at: '2026-03-08T08:00:00+08:00',
            updated_at: '2026-03-08T08:00:00+08:00',
          },
        ],
        total: 1,
        message: 'ok',
      })
    fetchCompanyDetailMock.mockResolvedValue({
      company_id: 'AUTO-TEST-OPERATOR-001',
      company_name: '运营商一号',
      company_type: 'operator_company',
      parent_company_id: null,
      parent_company_name: null,
      status: '启用',
      is_active: true,
      remark: null,
      child_company_count: 0,
      created_at: '2026-03-08T08:00:00+08:00',
      updated_at: '2026-03-08T08:00:00+08:00',
      created_by: 'admin',
      updated_by: 'admin',
      message: 'ok',
    })
    createCompanyMock.mockResolvedValue({ company_id: 'AUTO-TEST-SUPPLIER-NEW', message: '公司创建成功' })
    updateCompanyMock.mockResolvedValue({ company_id: 'AUTO-TEST-OPERATOR-001', message: '公司信息已更新' })
    updateCompanyStatusMock.mockResolvedValue({ company_id: 'AUTO-TEST-OPERATOR-001', message: '公司已停用' })

    const component = await import('./OrgCompaniesView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).openCreateDialog('supplier_company')
    ;(wrapper.vm as any).editorDialog.companyId = 'AUTO-TEST-SUPPLIER-NEW'
    ;(wrapper.vm as any).editorDialog.companyName = '供应商新档案'
    ;(wrapper.vm as any).editorDialog.parentCompanyId = 'AUTO-TEST-OPERATOR-001'
    ;(wrapper.vm as any).editorDialog.remark = '新增供应商'
    await (wrapper.vm as any).submitEditorDialog()

    expect(createCompanyMock).toHaveBeenCalledWith({
      company_id: 'AUTO-TEST-SUPPLIER-NEW',
      company_name: '供应商新档案',
      company_type: 'supplier_company',
      parent_company_id: 'AUTO-TEST-OPERATOR-001',
      remark: '新增供应商',
    })

    ;(wrapper.vm as any).selectedCompany = {
      ...(wrapper.vm as any).selectedCompany,
      company_id: 'AUTO-TEST-OPERATOR-001',
      company_name: '运营商一号',
      company_type: 'operator_company',
      parent_company_id: null,
      is_active: true,
    }
    ;(wrapper.vm as any).openEditDialog()
    ;(wrapper.vm as any).editorDialog.companyName = '运营商一号-更新'
    ;(wrapper.vm as any).editorDialog.remark = '更新备注'
    await (wrapper.vm as any).submitEditorDialog()
    expect(updateCompanyMock).toHaveBeenCalledWith('AUTO-TEST-OPERATOR-001', {
      company_name: '运营商一号-更新',
      parent_company_id: undefined,
      remark: '更新备注',
    })

    ;(wrapper.vm as any).openStatusDialog(false)
    ;(wrapper.vm as any).statusDialog.reason = '停用测试'
    await (wrapper.vm as any).submitStatusDialog()
    expect(updateCompanyStatusMock).toHaveBeenCalledWith('AUTO-TEST-OPERATOR-001', {
      enabled: false,
      reason: '停用测试',
    })
  }, 10000)

  it('非管理员角色不会触发公司列表加载', async () => {
    authState.session.roleCode = 'finance'
    fetchCompaniesMock.mockReset()

    const component = await import('./OrgCompaniesView.vue')
    shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchCompaniesMock).not.toHaveBeenCalled()
  }, 10000)
})
