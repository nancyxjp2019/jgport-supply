import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const authState = reactive({
  session: { roleCode: 'finance' },
})

const fetchContractsMock = vi.fn().mockResolvedValue({
  items: [
    {
      id: 5401,
      contract_no: 'CG-DEMO-5401',
      direction: 'purchase',
      status: '草稿',
      supplier_id: 'AUTO-TEST-SUPPLIER-5401',
      customer_id: null,
      close_type: null,
      created_at: '2026-03-08T08:20:00+08:00',
    },
  ],
  total: 1,
  message: 'ok',
})
const fetchContractDetailMock = vi.fn().mockResolvedValue({
  id: 5401,
  contract_no: 'CG-DEMO-5401',
  direction: 'purchase',
  status: '草稿',
  supplier_id: 'AUTO-TEST-SUPPLIER-5401',
  customer_id: null,
  close_type: null,
  created_at: '2026-03-08T08:20:00+08:00',
  threshold_release_snapshot: null,
  threshold_over_exec_snapshot: null,
  closed_by: null,
  closed_at: null,
  manual_close_reason: null,
  manual_close_by: null,
  manual_close_at: null,
  manual_close_diff_amount: null,
  manual_close_diff_qty_json: null,
  submit_comment: null,
  approval_comment: null,
  approved_by: null,
  submitted_at: null,
  approved_at: null,
  generated_task_count: 0,
  items: [
    {
      id: 1,
      oil_product_id: 'OIL-92',
      qty_signed: '120.000',
      unit_price: '6320.50',
      qty_in_acc: '0.000',
      qty_out_acc: '0.000',
    },
  ],
  message: 'ok',
})
const fetchContractGraphMock = vi.fn().mockResolvedValue({
  contract_id: 5401,
  contract_no: 'CG-DEMO-5401',
  direction: 'purchase',
  status: '草稿',
  downstream_tasks: [],
  message: 'ok',
})
const createPurchaseContractMock = vi.fn().mockResolvedValue({ id: 6401, message: '创建成功' })
const createSalesContractMock = vi.fn().mockResolvedValue({ id: 6402, message: '创建成功' })
const updateContractMock = vi.fn().mockResolvedValue({ id: 5401, message: '更新成功' })
const submitContractMock = vi.fn().mockResolvedValue({ id: 5401, message: '提交成功' })
const approveContractMock = vi.fn().mockResolvedValue({ id: 5401, message: '审批成功' })

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

vi.mock('@/api/contracts', () => ({
  fetchContracts: fetchContractsMock,
  fetchContractDetail: fetchContractDetailMock,
  fetchContractGraph: fetchContractGraphMock,
  createPurchaseContract: createPurchaseContractMock,
  createSalesContract: createSalesContractMock,
  updateContract: updateContractMock,
  submitContract: submitContractMock,
  approveContract: approveContractMock,
}))

describe('ContractsView', () => {
  it('挂载后加载合同列表、详情与图谱摘要', async () => {
    authState.session.roleCode = 'finance'
    const component = await import('./ContractsView.vue')
    shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchContractsMock).toHaveBeenCalledWith({ status: undefined, direction: undefined })
    expect(fetchContractDetailMock).toHaveBeenCalledWith(5401)
    expect(fetchContractGraphMock).toHaveBeenCalledWith(5401)
  }, 10000)

  it('财务可创建采购合同草稿', async () => {
    authState.session.roleCode = 'finance'
    fetchContractsMock.mockClear()
    fetchContractDetailMock.mockClear()
    fetchContractGraphMock.mockClear()
    createPurchaseContractMock.mockClear()

    const component = await import('./ContractsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).openCreateDialog('purchase')
    ;(wrapper.vm as any).createDialog.contractNo = 'CODEX-TEST-PC-6401'
    ;(wrapper.vm as any).createDialog.counterpartyId = 'CODEX-TEST-SUPPLIER-6401'
    ;(wrapper.vm as any).createDialog.items = [{ oil_product_id: 'OIL-92', qty_signed: 88.5, unit_price: 6200 }]
    await (wrapper.vm as any).submitCreate()

    expect(createPurchaseContractMock).toHaveBeenCalledWith({
      contract_no: 'CODEX-TEST-PC-6401',
      supplier_id: 'CODEX-TEST-SUPPLIER-6401',
      items: [{ oil_product_id: 'OIL-92', qty_signed: 88.5, unit_price: 6200 }],
    })
  }, 10000)

  it('财务可创建销售合同草稿并按筛选重新加载列表', async () => {
    authState.session.roleCode = 'finance'
    fetchContractsMock.mockClear()
    createSalesContractMock.mockClear()

    const component = await import('./ContractsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).directionFilter = 'sales'
    ;(wrapper.vm as any).statusFilter = '待审批'
    await (wrapper.vm as any).reloadContracts()

    ;(wrapper.vm as any).openCreateDialog('sales')
    ;(wrapper.vm as any).createDialog.contractNo = 'CODEX-TEST-SC-6402'
    ;(wrapper.vm as any).createDialog.counterpartyId = 'CODEX-TEST-CUSTOMER-6402'
    ;(wrapper.vm as any).createDialog.items = [{ oil_product_id: 'OIL-95', qty_signed: 66.6, unit_price: 6580 }]
    await (wrapper.vm as any).submitCreate()

    expect(fetchContractsMock).toHaveBeenLastCalledWith({ status: '待审批', direction: 'sales' })
    expect(createSalesContractMock).toHaveBeenCalledWith({
      contract_no: 'CODEX-TEST-SC-6402',
      customer_id: 'CODEX-TEST-CUSTOMER-6402',
      items: [{ oil_product_id: 'OIL-95', qty_signed: 66.6, unit_price: 6580 }],
    })
  }, 10000)

  it('财务可提交草稿并审批待审批合同', async () => {
    authState.session.roleCode = 'finance'
    submitContractMock.mockClear()
    approveContractMock.mockClear()

    const component = await import('./ContractsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).submitDialog.comment = '提审说明'
    await (wrapper.vm as any).submitCurrentContract()

    ;(wrapper.vm as any).selectedContract = {
      ...(wrapper.vm as any).selectedContract,
      status: '待审批',
    }
    ;(wrapper.vm as any).approvalDialog.comment = '审批通过'
    ;(wrapper.vm as any).approvalDialog.result = true
    await (wrapper.vm as any).submitApproval()

    expect(submitContractMock).toHaveBeenCalledWith(5401, { comment: '提审说明' })
    expect(approveContractMock).toHaveBeenCalledWith(5401, { approval_result: true, comment: '审批通过' })
  }, 10000)

  it('财务可编辑退回草稿并保存修改', async () => {
    authState.session.roleCode = 'finance'
    updateContractMock.mockClear()

    const component = await import('./ContractsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).selectedContract = {
      ...(wrapper.vm as any).selectedContract,
      status: '草稿',
      direction: 'sales',
      contract_no: 'XS-DEMO-REJECT-5401',
      customer_id: 'AUTO-TEST-CUSTOMER-OLD',
      supplier_id: null,
      approval_comment: '资料不完整，退回修改',
      items: [{ oil_product_id: 'OIL-92', qty_signed: '80.000', unit_price: '6200.00', qty_in_acc: '0.000', qty_out_acc: '0.000' }],
    }

    ;(wrapper.vm as any).openEditDialog()
    ;(wrapper.vm as any).createDialog.contractNo = 'CODEX-TEST-SC-EDIT-5401'
    ;(wrapper.vm as any).createDialog.counterpartyId = 'CODEX-TEST-CUSTOMER-EDIT'
    ;(wrapper.vm as any).createDialog.items = [{ oil_product_id: 'OIL-95', qty_signed: 55.5, unit_price: 6588 }]
    await (wrapper.vm as any).submitCreate()

    expect(updateContractMock).toHaveBeenCalledWith(5401, {
      contract_no: 'CODEX-TEST-SC-EDIT-5401',
      supplier_id: undefined,
      customer_id: 'CODEX-TEST-CUSTOMER-EDIT',
      items: [{ oil_product_id: 'OIL-95', qty_signed: 55.5, unit_price: 6588 }],
    })
  }, 10000)

  it('运营角色仅可回看，不能创建或审批', async () => {
    authState.session.roleCode = 'operations'
    submitContractMock.mockClear()
    approveContractMock.mockClear()
    updateContractMock.mockClear()
    const component = await import('./ContractsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).submitDialog.comment = '越权提审'
    await (wrapper.vm as any).submitCurrentContract()
    ;(wrapper.vm as any).selectedContract = {
      ...(wrapper.vm as any).selectedContract,
      status: '待审批',
    }
    ;(wrapper.vm as any).approvalDialog.comment = '越权审批'
    await (wrapper.vm as any).submitApproval()

    expect((wrapper.vm as any).canWriteContract).toBe(false)
    expect((wrapper.vm as any).canApproveContract).toBe(false)
    expect(submitContractMock).not.toHaveBeenCalled()
    expect(approveContractMock).not.toHaveBeenCalled()
    expect(updateContractMock).not.toHaveBeenCalled()
  }, 10000)

  it('非后台允许角色不会触发合同列表加载', async () => {
    authState.session.roleCode = 'customer'
    fetchContractsMock.mockClear()

    const component = await import('./ContractsView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    expect((wrapper.vm as any).canViewContracts).toBe(false)
    expect(fetchContractsMock).not.toHaveBeenCalled()
  }, 10000)
})
