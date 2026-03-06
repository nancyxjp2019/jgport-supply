export type LoginMode = 'demo' | 'proxy'

export interface AccessProfile {
  user_id: string
  role_code: string
  company_id: string | null
  company_type: string
  client_type: string
  admin_web_allowed: boolean
  miniprogram_allowed: boolean
  message: string
}

export interface AccessCheckResponse {
  allowed: boolean
  message: string
}

export interface AuthSession {
  userId: string
  roleCode: string
  roleLabel: string
  companyId: string | null
  companyType: string
  clientType: string
  loginMode: LoginMode
}
