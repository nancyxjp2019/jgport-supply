import type { AuthSession } from '@/types/auth'

export const AUTH_SESSION_STORAGE_KEY = 'jgport-admin-session'

export const ADMIN_WEB_DEMO_ROLES = [
  {
    roleCode: 'operations',
    roleLabel: '运营',
    description: '聚焦经营监控、履约推进和异常协调。',
  },
  {
    roleCode: 'finance',
    roleLabel: '财务',
    description: '聚焦实收实付、金额补录和闭环核对。',
  },
  {
    roleCode: 'admin',
    roleLabel: '管理员',
    description: '聚焦系统管理、审计追踪和参数中心。',
  },
] as const

const ROLE_LABEL_MAP: Record<string, string> = {
  operations: '运营',
  finance: '财务',
  admin: '管理员',
  customer: '客户',
  supplier: '供应商',
  warehouse: '仓库',
}

export function getRoleLabel(roleCode: string): string {
  return ROLE_LABEL_MAP[roleCode] ?? '未知角色'
}

export function isAdminWebAllowedRole(roleCode: string): boolean {
  return ADMIN_WEB_DEMO_ROLES.some((item) => item.roleCode === roleCode)
}

export function buildDemoSession(roleCode: string): AuthSession {
  if (!isAdminWebAllowedRole(roleCode)) {
    throw new Error('当前角色不允许登录管理后台')
  }
  return {
    userId: `AUTO-TEST-WEB-${roleCode.toUpperCase()}`,
    roleCode,
    roleLabel: getRoleLabel(roleCode),
    companyId: 'AUTO-TEST-OPERATOR-COMPANY',
    companyType: 'operator_company',
    clientType: 'admin_web',
    loginMode: 'demo',
  }
}

export function parseStoredSession(rawValue: string | null): AuthSession | null {
  if (!rawValue) {
    return null
  }
  try {
    const parsed = JSON.parse(rawValue) as Partial<AuthSession>
    if (
      typeof parsed.userId === 'string' &&
      typeof parsed.roleCode === 'string' &&
      typeof parsed.roleLabel === 'string' &&
      typeof parsed.companyType === 'string' &&
      typeof parsed.clientType === 'string' &&
      (parsed.loginMode === 'demo' || parsed.loginMode === 'proxy')
    ) {
      return {
        userId: parsed.userId,
        roleCode: parsed.roleCode,
        roleLabel: parsed.roleLabel,
        companyId: typeof parsed.companyId === 'string' ? parsed.companyId : null,
        companyType: parsed.companyType,
        clientType: parsed.clientType,
        loginMode: parsed.loginMode,
      }
    }
  } catch (_error) {
    return null
  }
  return null
}
