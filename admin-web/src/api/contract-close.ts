import {
  getDemoContractDetail,
  listDemoContracts,
  manualCloseDemoContract,
} from '@/mock/contract-close'

import { httpClient, reportsMode } from './http'

export interface ContractListItem {
  id: number
  contract_no: string
  direction: string
  status: string
  supplier_id: string | null
  customer_id: string | null
  close_type: string | null
  closed_by: string | null
  closed_at: string | null
  manual_close_reason: string | null
  manual_close_by: string | null
  manual_close_at: string | null
  manual_close_diff_amount: string | null
  manual_close_diff_qty_json: Array<Record<string, string>> | null
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

export interface ContractListResponse {
  items: ContractListItem[]
  total: number
  message: string
}

export interface ContractDetailResponse extends ContractListItem {
  threshold_release_snapshot: string | null
  threshold_over_exec_snapshot: string | null
  submit_comment: string | null
  approval_comment: string | null
  approved_by: string | null
  submitted_at: string | null
  approved_at: string | null
  items: ContractItem[]
  generated_task_count: number
  message: string
}

export interface ManualClosePayload {
  reason: string
  confirm_token: string
}

export async function fetchCloseContracts(params?: {
  status?: string
  direction?: string
  close_type?: string
}): Promise<ContractListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(listDemoContracts(params))
  }
  const { data } = await httpClient.get<ContractListResponse>('/contracts', {
    params: {
      ...(params?.status ? { status: params.status } : {}),
      ...(params?.direction ? { direction: params.direction } : {}),
      ...(params?.close_type ? { close_type: params.close_type } : {}),
      limit: 50,
    },
  })
  return data
}

export async function fetchCloseContractDetail(contractId: number): Promise<ContractDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoContractDetail(contractId))
  }
  const { data } = await httpClient.get<ContractDetailResponse>(`/contracts/${contractId}`)
  return data
}

export async function submitManualClose(contractId: number, payload: ManualClosePayload): Promise<ContractDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(manualCloseDemoContract(contractId, payload))
  }
  const { data } = await httpClient.post<ContractDetailResponse>(`/contracts/${contractId}/manual-close`, payload)
  return data
}
