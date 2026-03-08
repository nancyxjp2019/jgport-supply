import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const authState = reactive({
  session: { roleCode: 'finance' },
})

function createContractsState() {
  return [
    {
      id: 5301,
      contract_no: 'XS-CHAIN-5301',
      direction: 'sales',
      status: '已关闭',
      supplier_id: null,
      customer_id: 'CODEX-TEST-CUSTOMER-5301',
      close_type: 'AUTO',
      closed_by: 'CODEX-TEST-WH-CLOSE-5301',
      closed_at: '2026-03-09T11:20:00+08:00',
      manual_close_reason: null,
      manual_close_by: null,
      manual_close_at: null,
      manual_close_diff_amount: null,
      manual_close_diff_qty_json: null,
      threshold_release_snapshot: '0.980',
      threshold_over_exec_snapshot: '1.050',
      submit_comment: 'CODEX-TEST-提交审批',
      approval_comment: 'CODEX-TEST-审批通过',
      approved_by: 'CODEX-TEST-FINANCE-APPROVER',
      submitted_at: '2026-03-08T09:00:00+08:00',
      approved_at: '2026-03-08T10:00:00+08:00',
      created_at: '2026-03-08T08:40:00+08:00',
      generated_task_count: 2,
      items: [
        {
          id: 1,
          oil_product_id: 'OIL-92',
          qty_signed: '100.000',
          unit_price: '6500.25',
          qty_in_acc: '0.000',
          qty_out_acc: '100.000',
        },
      ],
      message: 'ok',
    },
    {
      id: 5302,
      contract_no: 'XS-CHAIN-5302',
      direction: 'sales',
      status: '数量履约完成',
      supplier_id: null,
      customer_id: 'CODEX-TEST-CUSTOMER-5302',
      close_type: null,
      closed_by: null,
      closed_at: null,
      manual_close_reason: null,
      manual_close_by: null,
      manual_close_at: null,
      manual_close_diff_amount: null,
      manual_close_diff_qty_json: null,
      threshold_release_snapshot: '0.980',
      threshold_over_exec_snapshot: '1.050',
      submit_comment: 'CODEX-TEST-提交审批',
      approval_comment: 'CODEX-TEST-审批通过',
      approved_by: 'CODEX-TEST-FINANCE-APPROVER',
      submitted_at: '2026-03-08T09:20:00+08:00',
      approved_at: '2026-03-08T10:10:00+08:00',
      created_at: '2026-03-08T09:05:00+08:00',
      generated_task_count: 2,
      items: [
        {
          id: 2,
          oil_product_id: 'OIL-95',
          qty_signed: '120.000',
          unit_price: '6720.80',
          qty_in_acc: '0.000',
          qty_out_acc: '120.000',
        },
      ],
      message: 'ok',
    },
    {
      id: 5303,
      contract_no: 'CG-CHAIN-5303',
      direction: 'purchase',
      status: '手工关闭',
      supplier_id: 'CODEX-TEST-SUPPLIER-5303',
      customer_id: null,
      close_type: 'MANUAL',
      closed_by: 'CODEX-TEST-FINANCE-CLOSE-5303',
      closed_at: '2026-03-09T10:20:00+08:00',
      manual_close_reason: '金额未闭环，手工关闭收口',
      manual_close_by: 'CODEX-TEST-FINANCE-CLOSE-5303',
      manual_close_at: '2026-03-09T10:20:00+08:00',
      manual_close_diff_amount: '3200.00',
      manual_close_diff_qty_json: [
        {
          oil_product_id: 'OIL-0',
          qty_signed: '80.000',
          qty_done: '80.000',
          diff_qty: '0.000',
        },
      ],
      threshold_release_snapshot: '0.980',
      threshold_over_exec_snapshot: '1.050',
      submit_comment: 'CODEX-TEST-提交审批',
      approval_comment: 'CODEX-TEST-审批通过',
      approved_by: 'CODEX-TEST-FINANCE-APPROVER',
      submitted_at: '2026-03-07T15:00:00+08:00',
      approved_at: '2026-03-07T16:10:00+08:00',
      created_at: '2026-03-07T14:40:00+08:00',
      generated_task_count: 2,
      items: [
        {
          id: 3,
          oil_product_id: 'OIL-0',
          qty_signed: '80.000',
          unit_price: '5988.60',
          qty_in_acc: '80.000',
          qty_out_acc: '0.000',
        },
      ],
      message: 'ok',
    },
  ]
}

function cloneContract(item: ReturnType<typeof createContractsState>[number]) {
  return {
    ...item,
    items: item.items.map((row) => ({ ...row })),
    manual_close_diff_qty_json: item.manual_close_diff_qty_json
      ? item.manual_close_diff_qty_json.map((row) => ({ ...row }))
      : null,
  }
}

let contractsState = createContractsState()

const fetchCloseContractsMock = vi.fn()
const fetchCloseContractDetailMock = vi.fn()
const submitManualCloseMock = vi.fn()

const messageWarning = vi.fn()
const messageSuccess = vi.fn()
const messageError = vi.fn()

const mountOptions = {
  global: {
    directives: {
      loading: () => undefined,
    },
  },
}

function listContracts(params?: { status?: string; direction?: string; close_type?: string }) {
  const items = contractsState.filter((item) => {
    if (params?.status && item.status !== params.status) {
      return false
    }
    if (params?.direction && item.direction !== params.direction) {
      return false
    }
    if (params?.close_type && item.close_type !== params.close_type) {
      return false
    }
    return true
  })
  return {
    items: items.map(cloneContract),
    total: items.length,
    message: 'ok',
  }
}

vi.mock('element-plus', async () => {
  const actual = await vi.importActual<typeof import('element-plus')>('element-plus')
  return {
    ...actual,
    ElMessage: {
      warning: messageWarning,
      success: messageSuccess,
      error: messageError,
    },
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authState,
}))

vi.mock('@/api/contract-close', () => ({
  fetchCloseContracts: fetchCloseContractsMock,
  fetchCloseContractDetail: fetchCloseContractDetailMock,
  submitManualClose: submitManualCloseMock,
}))

describe('ContractCloseView', () => {
  beforeEach(() => {
    authState.session.roleCode = 'finance'
    contractsState = createContractsState()
    fetchCloseContractsMock.mockReset()
    fetchCloseContractDetailMock.mockReset()
    submitManualCloseMock.mockReset()
    messageWarning.mockReset()
    messageSuccess.mockReset()
    messageError.mockReset()

    fetchCloseContractsMock.mockImplementation(async (params?: { status?: string; direction?: string; close_type?: string }) => listContracts(params))
    fetchCloseContractDetailMock.mockImplementation(async (contractId: number) => {
      const target = contractsState.find((item) => item.id === Number(contractId))
      if (!target) {
        throw new Error('合同不存在')
      }
      return cloneContract(target)
    })
    submitManualCloseMock.mockImplementation(async (contractId: number, payload: { reason: string; confirm_token: string }) => {
      const target = contractsState.find((item) => item.id === Number(contractId))
      if (!target) {
        throw new Error('合同不存在')
      }
      target.status = '手工关闭'
      target.close_type = 'MANUAL'
      target.closed_by = 'CODEX-TEST-FINANCE-MANUAL-CLOSE'
      target.closed_at = '2026-03-10T09:30:00+08:00'
      target.manual_close_by = 'CODEX-TEST-FINANCE-MANUAL-CLOSE'
      target.manual_close_at = '2026-03-10T09:30:00+08:00'
      target.manual_close_reason = payload.reason
      target.manual_close_diff_amount = '2800.00'
      target.manual_close_diff_qty_json = [
        {
          oil_product_id: 'OIL-95',
          qty_signed: '120.000',
          qty_done: '120.000',
          diff_qty: '0.000',
        },
      ]
      target.message = '合同已手工关闭'
      return cloneContract(target)
    })
  })

  it('挂载后加载合同列表与首条自动关闭详情', async () => {
    const component = await import('./ContractCloseView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchCloseContractsMock).toHaveBeenCalledWith({ status: undefined, direction: undefined, close_type: undefined })
    expect(fetchCloseContractDetailMock).toHaveBeenCalledWith(5301)
    expect(wrapper.text()).toContain('共 3 条')
    expect((wrapper.vm as any).detailHint).toBe('当前合同已自动关闭，表示数量与金额链路已完成收口。')
  }, 10000)

  it('可按关闭条件筛选并兼容后端差异字段展示', async () => {
    const component = await import('./ContractCloseView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).directionFilter = 'purchase'
    ;(wrapper.vm as any).statusFilter = '手工关闭'
    ;(wrapper.vm as any).closeTypeFilter = 'MANUAL'
    await (wrapper.vm as any).reloadContracts()
    await flushPromises()

    expect(fetchCloseContractsMock).toHaveBeenLastCalledWith({ status: '手工关闭', direction: 'purchase', close_type: 'MANUAL' })
    expect(fetchCloseContractDetailMock).toHaveBeenLastCalledWith(5303)
    expect(wrapper.text()).toContain('共 1 条')
    expect((wrapper.vm as any).manualCloseDiffRows).toEqual([
      {
        oil_product_id: 'OIL-0',
        qty_signed: '80.000',
        qty_in_acc: '80.000',
        qty_out_acc: '0.000',
        qty_gap: '0.000',
      },
    ])
    expect((wrapper.vm as any).detailHint).toBe('当前合同已手工关闭，请重点回看关闭原因、差异金额与油品数量差异留痕。')
  }, 10000)

  it('财务可执行手工关闭并刷新当前合同', async () => {
    const component = await import('./ContractCloseView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    await (wrapper.vm as any).handleCurrentChange(contractsState[1])
    await flushPromises()

    ;(wrapper.vm as any).openManualCloseDialog()
    expect((wrapper.vm as any).manualCloseDialog.visible).toBe(true)

    ;(wrapper.vm as any).manualCloseDialog.reason = ''
    await (wrapper.vm as any).submitCurrentContractManualClose()
    expect(messageWarning).toHaveBeenCalledWith('手工关闭原因不能为空')

    ;(wrapper.vm as any).manualCloseDialog.reason = '金额未闭环，执行手工关闭'
    ;(wrapper.vm as any).manualCloseDialog.confirmToken = 'MANUAL_CLOSE'
    await (wrapper.vm as any).submitCurrentContractManualClose()
    await flushPromises()

    expect(submitManualCloseMock).toHaveBeenCalledWith(5302, {
      reason: '金额未闭环，执行手工关闭',
      confirm_token: 'MANUAL_CLOSE',
    })
    expect(messageSuccess).toHaveBeenCalledWith('合同已手工关闭')
    expect(fetchCloseContractsMock).toHaveBeenLastCalledWith({ status: undefined, direction: undefined, close_type: undefined })
    expect(fetchCloseContractDetailMock).toHaveBeenLastCalledWith(5302)
    expect((wrapper.vm as any).selectedContract.status).toBe('手工关闭')
    expect((wrapper.vm as any).manualCloseDialog.visible).toBe(false)
  }, 10000)

  it('运营角色只能回看，不能执行手工关闭', async () => {
    authState.session.roleCode = 'operations'

    const component = await import('./ContractCloseView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    await (wrapper.vm as any).handleCurrentChange(contractsState[1])
    await flushPromises()

    ;(wrapper.vm as any).openManualCloseDialog()
    ;(wrapper.vm as any).manualCloseDialog.reason = '越权关闭'
    ;(wrapper.vm as any).manualCloseDialog.confirmToken = 'MANUAL_CLOSE'
    await (wrapper.vm as any).submitCurrentContractManualClose()

    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行手工关闭动作')
    expect(submitManualCloseMock).not.toHaveBeenCalled()
  }, 10000)
})
