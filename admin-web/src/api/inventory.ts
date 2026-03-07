import {
  getDemoInboundDocDetail,
  getDemoOutboundDocDetail,
  listDemoInboundDocs,
  listDemoOutboundDocs,
} from '@/mock/inventory'

import { httpClient, reportsMode } from './http'

export interface InboundDocListItem {
  id: number
  doc_no: string
  contract_id: number
  purchase_order_id: number | null
  oil_product_id: string
  warehouse_id: string | null
  source_type: string
  actual_qty: string
  status: string
  submitted_at: string | null
  created_at: string
}

export interface OutboundDocListItem {
  id: number
  doc_no: string
  contract_id: number
  sales_order_id: number
  oil_product_id: string
  warehouse_id: string | null
  source_type: string
  source_ticket_no: string | null
  manual_ref_no: string | null
  actual_qty: string
  status: string
  submitted_at: string | null
  created_at: string
}

export interface InboundDocListResponse {
  items: InboundDocListItem[]
  total: number
  message: string
}

export interface OutboundDocListResponse {
  items: OutboundDocListItem[]
  total: number
  message: string
}

export interface InboundDocDetailResponse extends InboundDocListItem {
  message: string
}

export interface OutboundDocDetailResponse extends OutboundDocListItem {
  message: string
}

export async function fetchInboundDocs(params?: {
  status?: string
  source_type?: string
}): Promise<InboundDocListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(listDemoInboundDocs(params))
  }
  const { data } = await httpClient.get<InboundDocListResponse>('/inbound-docs', {
    params: {
      ...(params?.status ? { status: params.status } : {}),
      ...(params?.source_type ? { source_type: params.source_type } : {}),
      limit: 50,
    },
  })
  return data
}

export async function fetchOutboundDocs(params?: {
  status?: string
  source_type?: string
}): Promise<OutboundDocListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(listDemoOutboundDocs(params))
  }
  const { data } = await httpClient.get<OutboundDocListResponse>('/outbound-docs', {
    params: {
      ...(params?.status ? { status: params.status } : {}),
      ...(params?.source_type ? { source_type: params.source_type } : {}),
      limit: 50,
    },
  })
  return data
}

export async function fetchInboundDocDetail(docId: number): Promise<InboundDocDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoInboundDocDetail(docId))
  }
  const { data } = await httpClient.get<InboundDocDetailResponse>(`/inbound-docs/${docId}`)
  return data
}

export async function fetchOutboundDocDetail(docId: number): Promise<OutboundDocDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoOutboundDocDetail(docId))
  }
  const { data } = await httpClient.get<OutboundDocDetailResponse>(`/outbound-docs/${docId}`)
  return data
}
