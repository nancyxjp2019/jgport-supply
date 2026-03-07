import {
  approveDemoSalesOrderByFinance,
  approveDemoSalesOrderByOps,
  getDemoSalesOrderDetail,
  listDemoSalesOrders,
} from '@/mock/orders'

import { httpClient, reportsMode } from './http'

export interface SalesOrderListItem {
  id: number
  order_no: string
  sales_contract_id: number
  sales_contract_no: string
  oil_product_id: string
  qty_ordered: string
  unit_price: string
  status: string
  submit_comment: string | null
  ops_comment: string | null
  finance_comment: string | null
  purchase_order_id: number | null
  submitted_at: string | null
  created_at: string
}

export interface SalesOrderListResponse {
  items: SalesOrderListItem[]
  total: number
  message: string
}

export interface SalesOrderDetailResponse extends SalesOrderListItem {
  message: string
  generated_task_count: number
}

export interface OpsApprovePayload {
  result: boolean
  comment: string
}

export interface FinanceApprovePayload {
  result: boolean
  purchase_contract_id?: number | null
  actual_receipt_amount?: number | null
  actual_pay_amount?: number | null
  comment: string
}

export async function fetchSalesOrders(status?: string): Promise<SalesOrderListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(listDemoSalesOrders(status))
  }
  const { data } = await httpClient.get<SalesOrderListResponse>('/sales-orders', {
    params: {
      ...(status ? { status } : {}),
      limit: 50,
    },
  })
  return data
}

export async function fetchSalesOrderDetail(orderId: number): Promise<SalesOrderDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoSalesOrderDetail(orderId))
  }
  const { data } = await httpClient.get<SalesOrderDetailResponse>(`/sales-orders/${orderId}`)
  return data
}

export async function approveSalesOrderByOps(orderId: number, payload: OpsApprovePayload): Promise<SalesOrderDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(approveDemoSalesOrderByOps(orderId, payload.result, payload.comment))
  }
  const { data } = await httpClient.post<SalesOrderDetailResponse>(`/sales-orders/${orderId}/ops-approve`, payload)
  return data
}

export async function approveSalesOrderByFinance(
  orderId: number,
  payload: FinanceApprovePayload,
): Promise<SalesOrderDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(approveDemoSalesOrderByFinance(orderId, payload))
  }
  const { data } = await httpClient.post<SalesOrderDetailResponse>(`/sales-orders/${orderId}/finance-approve`, payload)
  return data
}
