import type {
  ContractDetailResponse,
  ContractListResponse,
  ManualClosePayload,
} from '@/api/contract-close'

interface DemoContract extends ContractDetailResponse {}

const DEMO_CONTRACTS: DemoContract[] = [
  {
    id: 5301,
    contract_no: 'XS-DEMO-5301',
    direction: 'sales',
    status: '已关闭',
    supplier_id: null,
    customer_id: 'AUTO-TEST-CUSTOMER-5301',
    close_type: 'AUTO',
    closed_by: 'AUTO-TEST-WH-CLOSE-5301',
    closed_at: '2026-03-09T11:20:00+08:00',
    manual_close_reason: null,
    manual_close_by: null,
    manual_close_at: null,
    manual_close_diff_amount: null,
    manual_close_diff_qty_json: null,
    threshold_release_snapshot: '0.980',
    threshold_over_exec_snapshot: '1.050',
    submit_comment: 'AUTO-TEST-提交审批',
    approval_comment: 'AUTO-TEST-审批通过',
    approved_by: 'AUTO-TEST-FINANCE-APPROVER',
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
    message: '演示模式：合同详情查询成功',
  },
  {
    id: 5302,
    contract_no: 'XS-DEMO-5302',
    direction: 'sales',
    status: '数量履约完成',
    supplier_id: null,
    customer_id: 'AUTO-TEST-CUSTOMER-5302',
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
    submit_comment: 'AUTO-TEST-提交审批',
    approval_comment: 'AUTO-TEST-审批通过',
    approved_by: 'AUTO-TEST-FINANCE-APPROVER',
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
    message: '演示模式：合同详情查询成功',
  },
  {
    id: 5303,
    contract_no: 'CG-DEMO-5303',
    direction: 'purchase',
    status: '手工关闭',
    supplier_id: 'AUTO-TEST-SUPPLIER-5303',
    customer_id: null,
    close_type: 'MANUAL',
    closed_by: 'AUTO-TEST-FINANCE-CLOSE-5303',
    closed_at: '2026-03-09T10:20:00+08:00',
    manual_close_reason: '金额未闭环，手工关闭收口',
    manual_close_by: 'AUTO-TEST-FINANCE-CLOSE-5303',
    manual_close_at: '2026-03-09T10:20:00+08:00',
    manual_close_diff_amount: '3200.00',
    manual_close_diff_qty_json: [
      {
        oil_product_id: 'OIL-0',
        qty_signed: '80.000',
        qty_in_acc: '80.000',
        qty_out_acc: '0.000',
        qty_gap: '0.000',
      },
    ],
    threshold_release_snapshot: '0.980',
    threshold_over_exec_snapshot: '1.050',
    submit_comment: 'AUTO-TEST-提交审批',
    approval_comment: 'AUTO-TEST-审批通过',
    approved_by: 'AUTO-TEST-FINANCE-APPROVER',
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
    message: '演示模式：合同详情查询成功',
  },
]

function cloneContract(item: DemoContract): DemoContract {
  return {
    ...item,
    items: item.items.map((row) => ({ ...row })),
    manual_close_diff_qty_json: item.manual_close_diff_qty_json
      ? item.manual_close_diff_qty_json.map((row) => ({ ...row }))
      : null,
  }
}

function getContractOrThrow(contractId: number): DemoContract {
  const target = DEMO_CONTRACTS.find((item) => item.id === Number(contractId))
  if (!target) {
    throw new Error('当前合同不存在，请刷新后重试')
  }
  return target
}

function buildManualDiffQtyJson(target: DemoContract): Array<Record<string, string>> {
  return target.items.map((item) => {
    const qtySigned = Number(item.qty_signed)
    const qtyInAcc = Number(item.qty_in_acc)
    const qtyOutAcc = Number(item.qty_out_acc)
    const qtyDone = target.direction === 'purchase' ? qtyInAcc : qtyOutAcc
    const qtyGap = Math.max(qtySigned - qtyDone, 0)
    return {
      oil_product_id: item.oil_product_id,
      qty_signed: item.qty_signed,
      qty_in_acc: item.qty_in_acc,
      qty_out_acc: item.qty_out_acc,
      qty_gap: qtyGap.toFixed(3),
    }
  })
}

export function listDemoContracts(params?: {
  status?: string
  direction?: string
  close_type?: string
}): ContractListResponse {
  const normalizedStatus = String(params?.status || '').trim()
  const normalizedDirection = String(params?.direction || '').trim().toLowerCase()
  const normalizedCloseType = String(params?.close_type || '').trim()
  const filtered = DEMO_CONTRACTS.filter((item) => {
    if (normalizedStatus && item.status !== normalizedStatus) {
      return false
    }
    if (normalizedDirection && item.direction !== normalizedDirection) {
      return false
    }
    if (normalizedCloseType && item.close_type !== normalizedCloseType) {
      return false
    }
    return true
  })
  return {
    items: filtered.map(cloneContract),
    total: filtered.length,
    message: '演示模式：合同列表查询成功',
  }
}

export function getDemoContractDetail(contractId: number): ContractDetailResponse {
  return cloneContract(getContractOrThrow(contractId))
}

export function manualCloseDemoContract(contractId: number, payload: ManualClosePayload): ContractDetailResponse {
  const target = getContractOrThrow(contractId)
  const reason = String(payload.reason || '').trim()
  const confirmToken = String(payload.confirm_token || '').trim()

  if (!reason) {
    throw new Error('手工关闭原因不能为空')
  }
  if (confirmToken !== 'MANUAL_CLOSE') {
    throw new Error('手工关闭确认口令不正确')
  }
  if (target.status !== '数量履约完成') {
    throw new Error('合同未达到数量履约完成，禁止手工关闭')
  }

  const nowText = new Date().toISOString()
  target.status = '手工关闭'
  target.close_type = 'MANUAL'
  target.closed_by = 'AUTO-TEST-FINANCE-MANUAL-CLOSE'
  target.closed_at = nowText
  target.manual_close_reason = reason
  target.manual_close_by = 'AUTO-TEST-FINANCE-MANUAL-CLOSE'
  target.manual_close_at = nowText
  target.manual_close_diff_amount = '2800.00'
  target.manual_close_diff_qty_json = buildManualDiffQtyJson(target)
  target.message = '演示模式：合同手工关闭成功'
  return cloneContract(target)
}
