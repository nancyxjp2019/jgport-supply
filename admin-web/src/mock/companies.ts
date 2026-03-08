import type {
  CompanyCreatePayload,
  CompanyDetailResponse,
  CompanyListItem,
  CompanyListResponse,
  CompanyStatusPayload,
  CompanyUpdatePayload,
} from '@/api/companies'

interface DemoCompany extends CompanyDetailResponse {}

const DEMO_COMPANIES: DemoCompany[] = [
  {
    company_id: 'AUTO-TEST-OPERATOR-DEMO-001',
    company_name: 'AUTO-TEST-华东运营商',
    company_type: 'operator_company',
    parent_company_id: null,
    parent_company_name: null,
    status: '启用',
    is_active: true,
    remark: 'AUTO-TEST-运营主体',
    child_company_count: 3,
    created_at: '2026-03-08T08:00:00+08:00',
    updated_at: '2026-03-08T08:00:00+08:00',
    created_by: 'AUTO-TEST-ADMIN-001',
    updated_by: 'AUTO-TEST-ADMIN-001',
    message: '演示模式：公司详情查询成功',
  },
  {
    company_id: 'AUTO-TEST-CUSTOMER-DEMO-001',
    company_name: 'AUTO-TEST-客户一号',
    company_type: 'customer_company',
    parent_company_id: 'AUTO-TEST-OPERATOR-DEMO-001',
    parent_company_name: 'AUTO-TEST-华东运营商',
    status: '启用',
    is_active: true,
    remark: 'AUTO-TEST-客户档案',
    child_company_count: 0,
    created_at: '2026-03-08T08:10:00+08:00',
    updated_at: '2026-03-08T08:10:00+08:00',
    created_by: 'AUTO-TEST-ADMIN-001',
    updated_by: 'AUTO-TEST-ADMIN-001',
    message: '演示模式：公司详情查询成功',
  },
  {
    company_id: 'AUTO-TEST-SUPPLIER-DEMO-001',
    company_name: 'AUTO-TEST-供应商一号',
    company_type: 'supplier_company',
    parent_company_id: 'AUTO-TEST-OPERATOR-DEMO-001',
    parent_company_name: 'AUTO-TEST-华东运营商',
    status: '启用',
    is_active: true,
    remark: 'AUTO-TEST-供应商档案',
    child_company_count: 0,
    created_at: '2026-03-08T08:20:00+08:00',
    updated_at: '2026-03-08T08:20:00+08:00',
    created_by: 'AUTO-TEST-ADMIN-001',
    updated_by: 'AUTO-TEST-ADMIN-001',
    message: '演示模式：公司详情查询成功',
  },
  {
    company_id: 'AUTO-TEST-WAREHOUSE-DEMO-001',
    company_name: 'AUTO-TEST-仓库一号',
    company_type: 'warehouse_company',
    parent_company_id: 'AUTO-TEST-OPERATOR-DEMO-001',
    parent_company_name: 'AUTO-TEST-华东运营商',
    status: '停用',
    is_active: false,
    remark: 'AUTO-TEST-停用仓库',
    child_company_count: 0,
    created_at: '2026-03-08T08:30:00+08:00',
    updated_at: '2026-03-08T08:35:00+08:00',
    created_by: 'AUTO-TEST-ADMIN-001',
    updated_by: 'AUTO-TEST-ADMIN-001',
    message: '演示模式：公司详情查询成功',
  },
]

function cloneCompany(company: DemoCompany): DemoCompany {
  return { ...company }
}

function normalizeText(value: string | null | undefined): string {
  return String(value || '').trim()
}

function listChildren(parentCompanyId: string): DemoCompany[] {
  return DEMO_COMPANIES.filter((item) => item.parent_company_id === parentCompanyId && item.is_active)
}

function getCompanyOrThrow(companyId: string): DemoCompany {
  const target = DEMO_COMPANIES.find((item) => item.company_id === companyId)
  if (!target) {
    throw new Error('当前公司不存在，请刷新后重试')
  }
  return target
}

function updateChildCounts() {
  DEMO_COMPANIES.forEach((item) => {
    item.child_company_count = listChildren(item.company_id).length
  })
}

function resolveParentCompany(
  companyType: string,
  parentCompanyId?: string | null,
  currentCompanyId?: string,
): DemoCompany | null {
  const normalizedParentCompanyId = normalizeText(parentCompanyId)
  if (companyType === 'operator_company') {
    if (normalizedParentCompanyId) {
      throw new Error('运营商公司不能绑定上级公司')
    }
    return null
  }
  if (!normalizedParentCompanyId) {
    throw new Error('非运营商公司必须绑定归属运营商')
  }
  if (currentCompanyId && normalizedParentCompanyId === currentCompanyId) {
    throw new Error('公司不能归属到自身')
  }
  const parentCompany = DEMO_COMPANIES.find((item) => item.company_id === normalizedParentCompanyId)
  if (!parentCompany) {
    throw new Error('归属运营商公司不存在')
  }
  if (parentCompany.company_type !== 'operator_company') {
    throw new Error('归属公司必须是运营商公司')
  }
  if (!parentCompany.is_active) {
    throw new Error('归属运营商公司必须处于启用状态')
  }
  return parentCompany
}

function buildCompanyListItem(company: DemoCompany): CompanyListItem {
  updateChildCounts()
  return {
    company_id: company.company_id,
    company_name: company.company_name,
    company_type: company.company_type,
    parent_company_id: company.parent_company_id,
    parent_company_name: company.parent_company_name,
    status: company.status,
    is_active: company.is_active,
    remark: company.remark,
    child_company_count: company.child_company_count,
    created_at: company.created_at,
    updated_at: company.updated_at,
  }
}

export function listDemoCompanies(params?: {
  company_type?: string
  status?: string
}): CompanyListResponse {
  updateChildCounts()
  const items = DEMO_COMPANIES.filter((item) => (!params?.company_type || item.company_type === params.company_type))
    .filter((item) => (!params?.status || item.status === params.status))
    .map((item) => buildCompanyListItem(cloneCompany(item)))
  return {
    items,
    total: items.length,
    message: '演示模式：公司列表查询成功',
  }
}

export function getDemoCompanyDetail(companyId: string): CompanyDetailResponse {
  updateChildCounts()
  const target = cloneCompany(getCompanyOrThrow(companyId))
  target.message = '演示模式：公司详情查询成功'
  return target
}

export function createDemoCompany(payload: CompanyCreatePayload): CompanyDetailResponse {
  const companyId = normalizeText(payload.company_id)
  const companyName = normalizeText(payload.company_name)
  if (!companyId) {
    throw new Error('公司编码不能为空')
  }
  if (!companyName) {
    throw new Error('公司名称不能为空')
  }
  if (DEMO_COMPANIES.some((item) => item.company_id === companyId)) {
    throw new Error('公司编码已存在')
  }
  const parentCompany = resolveParentCompany(payload.company_type, payload.parent_company_id)
  const now = new Date().toISOString()
  const nextCompany: DemoCompany = {
    company_id: companyId,
    company_name: companyName,
    company_type: payload.company_type,
    parent_company_id: parentCompany?.company_id || null,
    parent_company_name: parentCompany?.company_name || null,
    status: '启用',
    is_active: true,
    remark: normalizeText(payload.remark) || null,
    child_company_count: 0,
    created_at: now,
    updated_at: now,
    created_by: 'AUTO-TEST-ADMIN-NEW',
    updated_by: 'AUTO-TEST-ADMIN-NEW',
    message: '演示模式：公司创建成功',
  }
  DEMO_COMPANIES.unshift(nextCompany)
  updateChildCounts()
  return cloneCompany(nextCompany)
}

export function updateDemoCompany(companyId: string, payload: CompanyUpdatePayload): CompanyDetailResponse {
  const target = getCompanyOrThrow(companyId)
  const companyName = normalizeText(payload.company_name)
  if (!companyName) {
    throw new Error('公司名称不能为空')
  }
  const parentCompany = resolveParentCompany(target.company_type, payload.parent_company_id, companyId)
  target.company_name = companyName
  target.parent_company_id = parentCompany?.company_id || null
  target.parent_company_name = parentCompany?.company_name || null
  target.remark = normalizeText(payload.remark) || null
  target.updated_by = 'AUTO-TEST-ADMIN-EDIT'
  target.updated_at = new Date().toISOString()
  target.message = '演示模式：公司信息已更新'
  updateChildCounts()
  return cloneCompany(target)
}

export function updateDemoCompanyStatus(companyId: string, payload: CompanyStatusPayload): CompanyDetailResponse {
  const target = getCompanyOrThrow(companyId)
  const reason = normalizeText(payload.reason)
  if (!reason) {
    throw new Error('状态变更原因不能为空')
  }
  if (!payload.enabled && listChildren(companyId).length > 0) {
    throw new Error('当前公司仍存在启用中的下级公司，禁止停用')
  }
  if (payload.enabled) {
    resolveParentCompany(target.company_type, target.parent_company_id, companyId)
  }
  target.is_active = payload.enabled
  target.status = payload.enabled ? '启用' : '停用'
  target.updated_by = 'AUTO-TEST-ADMIN-STATUS'
  target.updated_at = new Date().toISOString()
  target.message = payload.enabled ? '演示模式：公司已启用' : '演示模式：公司已停用'
  updateChildCounts()
  return cloneCompany(target)
}
