import {
  createDemoCompany,
  getDemoCompanyDetail,
  listDemoCompanies,
  updateDemoCompany,
  updateDemoCompanyStatus,
} from '@/mock/companies'

import { httpClient, reportsMode } from './http'

export interface CompanyListItem {
  company_id: string
  company_name: string
  company_type: string
  parent_company_id: string | null
  parent_company_name: string | null
  status: string
  is_active: boolean
  remark: string | null
  child_company_count: number
  created_at: string
  updated_at: string
}

export interface CompanyDetailResponse extends CompanyListItem {
  created_by: string
  updated_by: string
  message: string
}

export interface CompanyListResponse {
  items: CompanyListItem[]
  total: number
  message: string
}

export interface CompanyCreatePayload {
  company_id: string
  company_name: string
  company_type: string
  parent_company_id?: string | null
  remark?: string | null
}

export interface CompanyUpdatePayload {
  company_name: string
  parent_company_id?: string | null
  remark?: string | null
}

export interface CompanyStatusPayload {
  enabled: boolean
  reason: string
}

export async function fetchCompanies(params?: {
  company_type?: string
  status?: string
}): Promise<CompanyListResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(listDemoCompanies(params))
  }
  const { data } = await httpClient.get<CompanyListResponse>('/companies', {
    params: {
      ...(params?.company_type ? { company_type: params.company_type } : {}),
      ...(params?.status ? { status: params.status } : {}),
    },
  })
  return data
}

export async function fetchCompanyDetail(companyId: string): Promise<CompanyDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(getDemoCompanyDetail(companyId))
  }
  const { data } = await httpClient.get<CompanyDetailResponse>(`/companies/${companyId}`)
  return data
}

export async function createCompany(payload: CompanyCreatePayload): Promise<CompanyDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(createDemoCompany(payload))
  }
  const { data } = await httpClient.post<CompanyDetailResponse>('/companies', payload)
  return data
}

export async function updateCompany(companyId: string, payload: CompanyUpdatePayload): Promise<CompanyDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(updateDemoCompany(companyId, payload))
  }
  const { data } = await httpClient.put<CompanyDetailResponse>(`/companies/${companyId}`, payload)
  return data
}

export async function updateCompanyStatus(companyId: string, payload: CompanyStatusPayload): Promise<CompanyDetailResponse> {
  if (reportsMode === 'demo') {
    return Promise.resolve(updateDemoCompanyStatus(companyId, payload))
  }
  const { data } = await httpClient.post<CompanyDetailResponse>(`/companies/${companyId}/status`, payload)
  return data
}
