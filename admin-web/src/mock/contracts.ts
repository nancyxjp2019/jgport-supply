import type {
  ContractApprovePayload,
  ContractDetailResponse,
  ContractGraphResponse,
  ContractGraphTask,
  ContractItemPayload,
  ContractListResponse,
  ContractSubmitPayload,
  ContractUpdatePayload,
  PurchaseContractCreatePayload,
  SalesContractCreatePayload,
} from '@/api/contracts'

interface DemoContract extends ContractDetailResponse {
  downstream_tasks: ContractGraphTask[]
}

let demoContractSeed = 6400
let demoTaskSeed = 9100

const DEMO_CONTRACTS: DemoContract[] = [
  {
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
    submit_comment: 'AUTO-TEST-首轮提审后退回',
    approval_comment: 'AUTO-TEST-资料不完整，退回修改',
    approved_by: null,
    submitted_at: '2026-03-08T08:45:00+08:00',
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
    downstream_tasks: [],
    message: '演示模式：合同详情查询成功',
  },
  {
    id: 5402,
    contract_no: 'XS-DEMO-5402',
    direction: 'sales',
    status: '待审批',
    supplier_id: null,
    customer_id: 'AUTO-TEST-CUSTOMER-5402',
    close_type: null,
    created_at: '2026-03-08T09:00:00+08:00',
    threshold_release_snapshot: null,
    threshold_over_exec_snapshot: null,
    closed_by: null,
    closed_at: null,
    manual_close_reason: null,
    manual_close_by: null,
    manual_close_at: null,
    manual_close_diff_amount: null,
    manual_close_diff_qty_json: null,
    submit_comment: 'AUTO-TEST-待审批合同',
    approval_comment: null,
    approved_by: null,
    submitted_at: '2026-03-08T09:15:00+08:00',
    approved_at: null,
    generated_task_count: 0,
    items: [
      {
        id: 2,
        oil_product_id: 'OIL-95',
        qty_signed: '80.000',
        unit_price: '6680.10',
        qty_in_acc: '0.000',
        qty_out_acc: '0.000',
      },
    ],
    downstream_tasks: [],
    message: '演示模式：合同详情查询成功',
  },
  {
    id: 5403,
    contract_no: 'CG-DEMO-5403',
    direction: 'purchase',
    status: '生效中',
    supplier_id: 'AUTO-TEST-SUPPLIER-5403',
    customer_id: null,
    close_type: null,
    created_at: '2026-03-08T10:10:00+08:00',
    threshold_release_snapshot: '0.980',
    threshold_over_exec_snapshot: '1.050',
    closed_by: null,
    closed_at: null,
    manual_close_reason: null,
    manual_close_by: null,
    manual_close_at: null,
    manual_close_diff_amount: null,
    manual_close_diff_qty_json: null,
    submit_comment: 'AUTO-TEST-采购合同提审',
    approval_comment: 'AUTO-TEST-采购合同审批通过',
    approved_by: 'AUTO-TEST-FINANCE-5403',
    submitted_at: '2026-03-08T10:30:00+08:00',
    approved_at: '2026-03-08T11:00:00+08:00',
    generated_task_count: 2,
    items: [
      {
        id: 3,
        oil_product_id: 'OIL-0',
        qty_signed: '150.000',
        unit_price: '5998.60',
        qty_in_acc: '40.000',
        qty_out_acc: '0.000',
      },
    ],
    downstream_tasks: [
      {
        id: 9101,
        target_doc_type: 'payment_doc',
        status: '待处理',
        idempotency_key: 'AUTO-TEST-PAYMENT-5403',
      },
      {
        id: 9102,
        target_doc_type: 'inbound_doc',
        status: '待处理',
        idempotency_key: 'AUTO-TEST-INBOUND-5403',
      },
    ],
    message: '演示模式：合同详情查询成功',
  },
]

function cloneContract(contract: DemoContract): DemoContract {
  return {
    ...contract,
    items: contract.items.map((item) => ({ ...item })),
    downstream_tasks: contract.downstream_tasks.map((task) => ({ ...task })),
    manual_close_diff_qty_json: contract.manual_close_diff_qty_json
      ? contract.manual_close_diff_qty_json.map((item) => ({ ...item }))
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

function normalizeText(value: string | null | undefined): string {
  return String(value || '').trim()
}

function buildItemList(items: ContractItemPayload[]) {
  return items.map((item, index) => ({
    id: index + 1,
    oil_product_id: normalizeText(item.oil_product_id),
    qty_signed: Number(item.qty_signed).toFixed(3),
    unit_price: Number(item.unit_price).toFixed(2),
    qty_in_acc: '0.000',
    qty_out_acc: '0.000',
  }))
}

function validateEditablePayload(
  payload: PurchaseContractCreatePayload | SalesContractCreatePayload | ContractUpdatePayload,
  direction: 'purchase' | 'sales',
  currentContractId?: number,
) {
  const contractNo = normalizeText(payload.contract_no)
  const counterpartyId = direction === 'purchase'
    ? normalizeText((payload as PurchaseContractCreatePayload | ContractUpdatePayload).supplier_id)
    : normalizeText((payload as SalesContractCreatePayload | ContractUpdatePayload).customer_id)

  if (!contractNo) {
    throw new Error('合同编号不能为空')
  }
  if (!counterpartyId) {
    throw new Error(direction === 'purchase' ? '供应商不能为空' : '客户不能为空')
  }
  if (DEMO_CONTRACTS.some((item) => item.contract_no === contractNo && item.id !== currentContractId)) {
    throw new Error('合同编号已存在')
  }
  if (!payload.items.length) {
    throw new Error('至少需要一条油品明细')
  }
  const oilProductIds = payload.items.map((item) => normalizeText(item.oil_product_id))
  if (oilProductIds.some((item) => !item)) {
    throw new Error('油品不能为空')
  }
  if (new Set(oilProductIds).size !== oilProductIds.length) {
    throw new Error('同一合同下油品明细不能重复')
  }
  for (const item of payload.items) {
    if (!(Number(item.qty_signed) > 0)) {
      throw new Error('签约数量必须大于 0')
    }
    if (!(Number(item.unit_price) > 0)) {
      throw new Error('合同单价必须大于 0')
    }
  }
}

function buildDownstreamTasks(direction: string): ContractGraphTask[] {
  if (direction === 'purchase') {
    return [
      {
        id: ++demoTaskSeed,
        target_doc_type: 'payment_doc',
        status: '待生成',
        idempotency_key: `AUTO-TEST-PAYMENT-${demoTaskSeed}`,
      },
      {
        id: ++demoTaskSeed,
        target_doc_type: 'inbound_doc',
        status: '待生成',
        idempotency_key: `AUTO-TEST-INBOUND-${demoTaskSeed}`,
      },
    ]
  }
  return [
    {
      id: ++demoTaskSeed,
      target_doc_type: 'receipt_doc',
      status: '待处理',
      idempotency_key: `AUTO-TEST-RECEIPT-${demoTaskSeed}`,
    },
  ]
}

function createDemoContract(
  payload: PurchaseContractCreatePayload | SalesContractCreatePayload,
  direction: 'purchase' | 'sales',
): ContractDetailResponse {
  validateEditablePayload(payload, direction)
  const nowText = new Date().toISOString()
  const contractNo = normalizeText(payload.contract_no)
  const nextId = ++demoContractSeed
  const nextContract: DemoContract = {
    id: nextId,
    contract_no: contractNo,
    direction,
    status: '草稿',
    supplier_id: direction === 'purchase' ? normalizeText((payload as PurchaseContractCreatePayload).supplier_id) : null,
    customer_id: direction === 'sales' ? normalizeText((payload as SalesContractCreatePayload).customer_id) : null,
    close_type: null,
    created_at: nowText,
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
    items: buildItemList(payload.items),
    generated_task_count: 0,
    downstream_tasks: [],
    message: '演示模式：合同草稿创建成功',
  }
  DEMO_CONTRACTS.unshift(nextContract)
  return cloneContract(nextContract)
}

export function listDemoContracts(params?: {
  status?: string
  direction?: string
}): ContractListResponse {
  const normalizedStatus = normalizeText(params?.status)
  const normalizedDirection = normalizeText(params?.direction).toLowerCase()
  const filtered = DEMO_CONTRACTS.filter((item) => {
    if (normalizedStatus && item.status !== normalizedStatus) {
      return false
    }
    if (normalizedDirection && item.direction !== normalizedDirection) {
      return false
    }
    return true
  })
  return {
    items: filtered.map((item) => {
      const cloned = cloneContract(item)
      return {
        id: cloned.id,
        contract_no: cloned.contract_no,
        direction: cloned.direction,
        status: cloned.status,
        supplier_id: cloned.supplier_id,
        customer_id: cloned.customer_id,
        close_type: cloned.close_type,
        created_at: cloned.created_at,
      }
    }),
    total: filtered.length,
    message: '演示模式：合同列表查询成功',
  }
}

export function getDemoContractDetail(contractId: number): ContractDetailResponse {
  return cloneContract(getContractOrThrow(contractId))
}

export function getDemoContractGraph(contractId: number): ContractGraphResponse {
  const contract = cloneContract(getContractOrThrow(contractId))
  return {
    contract_id: contract.id,
    contract_no: contract.contract_no,
    direction: contract.direction,
    status: contract.status,
    downstream_tasks: contract.downstream_tasks,
    message: '演示模式：合同图谱查询成功',
  }
}

export function createDemoPurchaseContract(payload: PurchaseContractCreatePayload): ContractDetailResponse {
  return createDemoContract(payload, 'purchase')
}

export function createDemoSalesContract(payload: SalesContractCreatePayload): ContractDetailResponse {
  return createDemoContract(payload, 'sales')
}

export function updateDemoContract(contractId: number, payload: ContractUpdatePayload): ContractDetailResponse {
  const target = getContractOrThrow(contractId)
  if (target.status !== '草稿') {
    throw new Error('仅草稿合同可修改')
  }
  validateEditablePayload(payload, target.direction as 'purchase' | 'sales', target.id)
  target.contract_no = normalizeText(payload.contract_no)
  target.supplier_id = target.direction === 'purchase'
    ? normalizeText(payload.supplier_id)
    : null
  target.customer_id = target.direction === 'sales'
    ? normalizeText(payload.customer_id)
    : null
  target.items = buildItemList(payload.items)
  target.message = target.approval_comment
    ? '演示模式：合同草稿已更新，可再次提审'
    : '演示模式：合同草稿已更新'
  return cloneContract(target)
}

export function submitDemoContract(contractId: number, payload: ContractSubmitPayload): ContractDetailResponse {
  const target = getContractOrThrow(contractId)
  const comment = normalizeText(payload.comment)
  if (!comment) {
    throw new Error('提交说明不能为空')
  }
  if (target.status !== '草稿') {
    throw new Error('仅草稿合同可提交审批')
  }
  target.status = '待审批'
  target.submit_comment = comment
  target.submitted_at = new Date().toISOString()
  target.approved_by = null
  target.approved_at = null
  target.threshold_release_snapshot = null
  target.threshold_over_exec_snapshot = null
  target.downstream_tasks = []
  target.generated_task_count = 0
  target.message = '演示模式：合同已提交审批'
  return cloneContract(target)
}

export function approveDemoContract(contractId: number, payload: ContractApprovePayload): ContractDetailResponse {
  const target = getContractOrThrow(contractId)
  const comment = normalizeText(payload.comment)
  if (!comment) {
    throw new Error('审批意见不能为空')
  }
  if (target.status !== '待审批') {
    throw new Error('仅待审批合同可执行审批')
  }
  target.approval_comment = comment
  target.approved_by = 'AUTO-TEST-FINANCE-APPROVER'
  target.approved_at = new Date().toISOString()
  if (payload.approval_result) {
    target.status = '生效中'
    target.threshold_release_snapshot = '0.980'
    target.threshold_over_exec_snapshot = '1.050'
    target.downstream_tasks = buildDownstreamTasks(target.direction)
    target.generated_task_count = target.downstream_tasks.length
    target.message = '演示模式：合同审批通过并已生效'
    return cloneContract(target)
  }
  target.status = '草稿'
  target.approved_by = null
  target.approved_at = null
  target.threshold_release_snapshot = null
  target.threshold_over_exec_snapshot = null
  target.downstream_tasks = []
  target.generated_task_count = 0
  target.message = '演示模式：合同已驳回并退回草稿'
  return cloneContract(target)
}
