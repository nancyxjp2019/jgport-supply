import {
  confirmDemoPaymentDoc,
  confirmDemoReceiptDoc,
  createDemoPaymentSupplement,
  createDemoReceiptSupplement,
  getDemoPaymentDocDetail,
  getDemoReceiptDocDetail,
  listDemoPaymentDocs,
  listDemoReceiptDocs,
} from '@/mock/funds'

import { httpClient, reportsMode } from './http'

export interface PaymentDocListItem {
  id: number
  doc_no: string
  doc_type: string
  contract_id: number
  purchase_order_id: number | null
  amount_actual: string
  status: string
  voucher_required: boolean
  voucher_exempt_reason: string | null
  refund_status: string
  refund_amount: string
  confirmed_at: string | null
  created_at: string
}

export interface ReceiptDocListItem {
  id: number
  doc_no: string
  doc_type: string
  contract_id: number
  sales_order_id: number | null
  amount_actual: string
  status: string
  voucher_required: boolean
  voucher_exempt_reason: string | null
  refund_status: string
  refund_amount: string
  confirmed_at: string | null
  created_at: string
}

export interface PaymentDocListResponse {
  items: PaymentDocListItem[]
  total: number
  message: string
}

export interface ReceiptDocListResponse {
  items: ReceiptDocListItem[]
  total: number
  message: string
}

export interface PaymentDocDetailResponse extends PaymentDocListItem {
  voucher_file_paths: string[]
  message: string
}

export interface ReceiptDocDetailResponse extends ReceiptDocListItem {
  voucher_file_paths: string[]
  message: string
}

export interface PaymentDocSupplementPayload {
  contract_id: number
  purchase_order_id: number
  amount_actual: number
}

export interface ReceiptDocSupplementPayload {
  contract_id: number
  sales_order_id: number
  amount_actual: number
}

export interface FundDocConfirmPayload {
  amount_actual: number
  voucher_files: string[]
}

export async function fetchPaymentDocs(status?: string): Promise<PaymentDocListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(listDemoPaymentDocs(status))
  }
  const { data } = await httpClient.get<PaymentDocListResponse>('/payment-docs', {
    params: {
      ...(status ? { status } : {}),
      limit: 50,
    },
  })
  return data
}

export async function fetchReceiptDocs(status?: string): Promise<ReceiptDocListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(listDemoReceiptDocs(status))
  }
  const { data } = await httpClient.get<ReceiptDocListResponse>('/receipt-docs', {
    params: {
      ...(status ? { status } : {}),
      limit: 50,
    },
  })
  return data
}

export async function fetchPaymentDocDetail(docId: number): Promise<PaymentDocDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoPaymentDocDetail(docId))
  }
  const { data } = await httpClient.get<PaymentDocDetailResponse>(`/payment-docs/${docId}`)
  return data
}

export async function fetchReceiptDocDetail(docId: number): Promise<ReceiptDocDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoReceiptDocDetail(docId))
  }
  const { data } = await httpClient.get<ReceiptDocDetailResponse>(`/receipt-docs/${docId}`)
  return data
}

export async function createPaymentSupplement(payload: PaymentDocSupplementPayload): Promise<PaymentDocDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(createDemoPaymentSupplement(payload))
  }
  const { data } = await httpClient.post<PaymentDocDetailResponse>('/payment-docs/supplement', payload)
  return data
}

export async function createReceiptSupplement(payload: ReceiptDocSupplementPayload): Promise<ReceiptDocDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(createDemoReceiptSupplement(payload))
  }
  const { data } = await httpClient.post<ReceiptDocDetailResponse>('/receipt-docs/supplement', payload)
  return data
}

export async function confirmPaymentDoc(docId: number, payload: FundDocConfirmPayload): Promise<PaymentDocDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(confirmDemoPaymentDoc(docId, payload))
  }
  const { data } = await httpClient.post<PaymentDocDetailResponse>(`/payment-docs/${docId}/confirm`, payload)
  return data
}

export async function confirmReceiptDoc(docId: number, payload: FundDocConfirmPayload): Promise<ReceiptDocDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(confirmDemoReceiptDoc(docId, payload))
  }
  const { data } = await httpClient.post<ReceiptDocDetailResponse>(`/receipt-docs/${docId}/confirm`, payload)
  return data
}
