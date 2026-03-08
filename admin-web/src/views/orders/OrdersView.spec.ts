import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const authState = reactive({
  session: { roleCode: 'operations' },
})

const orderListResponse = {
  items: [
    {
      id: 7101,
      order_no: 'SO-DEMO-7101',
      sales_contract_id: 5201,
      sales_contract_no: 'XS-DEMO-5201',
      oil_product_id: 'OIL-92',
      qty_ordered: '20.000',
      unit_price: '6500.25',
      status: '待运营审批',
      submit_comment: 'AUTO-TEST-客户提交订单审批',
      ops_comment: null,
      finance_comment: null,
      purchase_order_id: null,
      submitted_at: '2026-03-08T09:10:00+08:00',
      created_at: '2026-03-08T08:50:00+08:00',
    },
  ],
  total: 1,
  message: 'ok',
}

const opsOrderDetail = {
  ...orderListResponse.items[0],
  generated_task_count: 0,
  message: 'ok',
}

const financeOrderDetail = {
  ...orderListResponse.items[0],
  id: 7102,
  order_no: 'SO-DEMO-7102',
  status: '待财务审批',
  ops_comment: 'AUTO-TEST-运营审批通过',
  generated_task_count: 0,
  message: 'ok',
}

const fetchSalesOrdersMock = vi.fn().mockResolvedValue(orderListResponse)
const fetchSalesOrderDetailMock = vi.fn().mockImplementation(async (orderId: number) => {
  return Number(orderId) === 7102 ? financeOrderDetail : opsOrderDetail
})
const approveSalesOrderByOpsMock = vi.fn().mockResolvedValue({
  ...opsOrderDetail,
  status: '待财务审批',
  ops_comment: '运营通过',
  message: '运营审批已提交',
})
const approveSalesOrderByFinanceMock = vi.fn().mockResolvedValue({
  ...financeOrderDetail,
  status: '已衍生采购订单',
  finance_comment: '财务通过',
  purchase_order_id: 9302,
  generated_task_count: 2,
  message: '财务审批已提交',
})

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

vi.mock('@/api/orders', () => ({
  fetchSalesOrders: fetchSalesOrdersMock,
  fetchSalesOrderDetail: fetchSalesOrderDetailMock,
  approveSalesOrderByOps: approveSalesOrderByOpsMock,
  approveSalesOrderByFinance: approveSalesOrderByFinanceMock,
}))

describe('OrdersView', () => {
  it('挂载后加载订单列表与详情', async () => {
    authState.session.roleCode = 'operations'
    const component = await import('./OrdersView.vue')
    shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchSalesOrdersMock).toHaveBeenCalledWith(undefined)
    expect(fetchSalesOrderDetailMock).toHaveBeenCalledWith(7101)
  }, 10000)

  it('运营可审批待运营订单', async () => {
    authState.session.roleCode = 'operations'
    approveSalesOrderByOpsMock.mockClear()
    fetchSalesOrdersMock.mockClear()

    const component = await import('./OrdersView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).opsDialog.comment = '运营通过'
    ;(wrapper.vm as any).opsDialog.result = true
    await (wrapper.vm as any).submitOpsApproval()

    expect(approveSalesOrderByOpsMock).toHaveBeenCalledWith(7101, {
      result: true,
      comment: '运营通过',
    })
    expect(fetchSalesOrdersMock).toHaveBeenLastCalledWith(undefined)
  }, 10000)

  it('财务可审批待财务订单并填写采购合同与实收实付', async () => {
    authState.session.roleCode = 'finance'
    approveSalesOrderByFinanceMock.mockClear()

    const component = await import('./OrdersView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).selectedOrderId = 7102
    ;(wrapper.vm as any).selectedOrder = { ...financeOrderDetail }
    ;(wrapper.vm as any).financeDialog.result = true
    ;(wrapper.vm as any).financeDialog.purchaseContractId = 8201
    ;(wrapper.vm as any).financeDialog.actualReceiptAmount = 12000.34
    ;(wrapper.vm as any).financeDialog.actualPayAmount = 11800.12
    ;(wrapper.vm as any).financeDialog.comment = '财务通过'
    await (wrapper.vm as any).submitFinanceApproval()

    expect(approveSalesOrderByFinanceMock).toHaveBeenCalledWith(7102, {
      result: true,
      purchase_contract_id: 8201,
      actual_receipt_amount: 12000.34,
      actual_pay_amount: 11800.12,
      comment: '财务通过',
    })
    expect(fetchSalesOrdersMock).toHaveBeenLastCalledWith(undefined)
  }, 10000)

  it('运营角色不能提交财务审批，财务角色不能提交运营审批', async () => {
    messageWarning.mockClear()
    approveSalesOrderByOpsMock.mockClear()
    approveSalesOrderByFinanceMock.mockClear()

    const component = await import('./OrdersView.vue')

    authState.session.roleCode = 'operations'
    const operationsWrapper = shallowMount(component.default, mountOptions)
    await flushPromises()
    ;(operationsWrapper.vm as any).selectedOrderId = 7102
    ;(operationsWrapper.vm as any).selectedOrder = { ...financeOrderDetail }
    ;(operationsWrapper.vm as any).financeDialog.result = true
    ;(operationsWrapper.vm as any).financeDialog.purchaseContractId = 8201
    ;(operationsWrapper.vm as any).financeDialog.actualReceiptAmount = 12000.34
    ;(operationsWrapper.vm as any).financeDialog.actualPayAmount = 11800.12
    ;(operationsWrapper.vm as any).financeDialog.comment = '越权财务审批'
    await (operationsWrapper.vm as any).submitFinanceApproval()

    authState.session.roleCode = 'finance'
    const financeWrapper = shallowMount(component.default, mountOptions)
    await flushPromises()
    ;(financeWrapper.vm as any).selectedOrderId = 7101
    ;(financeWrapper.vm as any).selectedOrder = { ...opsOrderDetail }
    ;(financeWrapper.vm as any).opsDialog.comment = '越权运营审批'
    ;(financeWrapper.vm as any).opsDialog.result = true
    await (financeWrapper.vm as any).submitOpsApproval()

    expect(approveSalesOrderByFinanceMock).not.toHaveBeenCalled()
    expect(approveSalesOrderByOpsMock).not.toHaveBeenCalled()
    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行财务审批动作')
    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行运营审批动作')
  }, 10000)

  it('管理员可执行运营与财务审批动作', async () => {
    authState.session.roleCode = 'admin'
    approveSalesOrderByOpsMock.mockClear()
    approveSalesOrderByFinanceMock.mockClear()

    const component = await import('./OrdersView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).selectedOrderId = 7101
    ;(wrapper.vm as any).selectedOrder = { ...opsOrderDetail }
    ;(wrapper.vm as any).opsDialog.comment = '管理员运营通过'
    ;(wrapper.vm as any).opsDialog.result = true
    await (wrapper.vm as any).submitOpsApproval()

    ;(wrapper.vm as any).selectedOrderId = 7102
    ;(wrapper.vm as any).selectedOrder = { ...financeOrderDetail }
    ;(wrapper.vm as any).financeDialog.result = true
    ;(wrapper.vm as any).financeDialog.purchaseContractId = 8201
    ;(wrapper.vm as any).financeDialog.actualReceiptAmount = 12000.34
    ;(wrapper.vm as any).financeDialog.actualPayAmount = 11800.12
    ;(wrapper.vm as any).financeDialog.comment = '管理员财务通过'
    await (wrapper.vm as any).submitFinanceApproval()

    expect(approveSalesOrderByOpsMock).toHaveBeenCalledWith(7101, {
      result: true,
      comment: '管理员运营通过',
    })
    expect(approveSalesOrderByFinanceMock).toHaveBeenCalledWith(7102, {
      result: true,
      purchase_contract_id: 8201,
      actual_receipt_amount: 12000.34,
      actual_pay_amount: 11800.12,
      comment: '管理员财务通过',
    })
  }, 10000)

  it('客户角色不能打开运营或财务审批弹窗', async () => {
    authState.session.roleCode = 'customer'
    messageWarning.mockClear()

    const component = await import('./OrdersView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).openOpsDialog(true)
    ;(wrapper.vm as any).openFinanceDialog(true)

    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行运营审批动作')
    expect(messageWarning).toHaveBeenCalledWith('当前角色无权执行财务审批动作')
  }, 10000)
})
