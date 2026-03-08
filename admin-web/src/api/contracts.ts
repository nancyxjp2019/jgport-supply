import {
  approveDemoContract,
  createDemoPurchaseContract,
  createDemoSalesContract,
  getDemoContractDetail,
  getDemoContractGraph,
  listDemoContracts,
  submitDemoContract,
  updateDemoContract,
} from '@/mock/contracts'

import { httpClient, reportsMode } from './http'

export interface ContractListItem {
  id: number
  contract_no: string
  direction: string
  status: string
  supplier_id: string | null
  customer_id: string | null
  close_type: string | null
  created_at: string
}

export interface ContractItem {
  id: number
  oil_product_id: string
  qty_signed: string
  unit_price: string
  qty_in_acc: string
  qty_out_acc: string
}

export interface ContractDetailResponse extends ContractListItem {
  threshold_release_snapshot: string | null
  threshold_over_exec_snapshot: string | null
  closed_by: string | null
  closed_at: string | null
  manual_close_reason: string | null
  manual_close_by: string | null
  manual_close_at: string | null
  manual_close_diff_amount: string | null
  manual_close_diff_qty_json: Array<Record<string, string>> | null
  submit_comment: string | null
  approval_comment: string | null
  approved_by: string | null
  submitted_at: string | null
  approved_at: string | null
  items: ContractItem[]
  generated_task_count: number
  message: string
}

export interface ContractListResponse {
  items: ContractListItem[]
  total: number
  message: string
}

export interface ContractGraphTask {
  id: number
  target_doc_type: string
  status: string
  idempotency_key: string
}

export interface ContractGraphResponse {
  contract_id: number
  contract_no: string
  direction: string
  status: string
  downstream_tasks: ContractGraphTask[]
  message: string
}

export interface ContractItemPayload {
  oil_product_id: string
  qty_signed: number
  unit_price: number
}

export interface PurchaseContractCreatePayload {
  contract_no: string
  supplier_id: string
  items: ContractItemPayload[]
}

export interface SalesContractCreatePayload {
  contract_no: string
  customer_id: string
  items: ContractItemPayload[]
}

export interface ContractSubmitPayload {
  comment: string
}

export interface ContractApprovePayload {
  approval_result: boolean
  comment: string
}

export interface ContractUpdatePayload {
  contract_no: string
  supplier_id?: string | null
  customer_id?: string | null
  items: ContractItemPayload[]
}

export async function fetchContracts(params?: {
  status?: string
  direction?: string
}): Promise<ContractListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(listDemoContracts(params))
  }
  const { data } = await httpClient.get<ContractListResponse>('/contracts', {
    params: {
      ...(params?.status ? { status: params.status } : {}),
      ...(params?.direction ? { direction: params.direction } : {}),
      limit: 50,
    },
  })
  return data
}

export async function fetchContractDetail(contractId: number): Promise<ContractDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoContractDetail(contractId))
  }
  const { data } = await httpClient.get<ContractDetailResponse>(`/contracts/${contractId}`)
  return data
}

export async function fetchContractGraph(contractId: number): Promise<ContractGraphResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoContractGraph(contractId))
  }
  const { data } = await httpClient.get<ContractGraphResponse>(`/contracts/${contractId}/graph`)
  return data
}

export async function createPurchaseContract(payload: PurchaseContractCreatePayload): Promise<ContractDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(createDemoPurchaseContract(payload))
  }
  const { data } = await httpClient.post<ContractDetailResponse>('/contracts/purchase', payload)
  return data
}

export async function createSalesContract(payload: SalesContractCreatePayload): Promise<ContractDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(createDemoSalesContract(payload))
  }
  const { data } = await httpClient.post<ContractDetailResponse>('/contracts/sales', payload)
  return data
}

export async function updateContract(contractId: number, payload: ContractUpdatePayload): Promise<ContractDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(updateDemoContract(contractId, payload))
  }
  const { data } = await httpClient.put<ContractDetailResponse>(`/contracts/${contractId}`, payload)
  return data
}

export async function submitContract(contractId: number, payload: ContractSubmitPayload): Promise<ContractDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(submitDemoContract(contractId, payload))
  }
  const { data } = await httpClient.post<ContractDetailResponse>(`/contracts/${contractId}/submit`, payload)
  return data
}

export async function approveContract(contractId: number, payload: ContractApprovePayload): Promise<ContractDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(approveDemoContract(contractId, payload))
  }
  const { data } = await httpClient.post<ContractDetailResponse>(`/contracts/${contractId}/approve`, payload)
  return data
}
