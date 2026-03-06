import { describe, expect, it } from 'vitest'

import { buildDemoSession, getRoleLabel, isAdminWebAllowedRole, parseStoredSession } from './auth'

describe('auth utils', () => {
  it('仅允许运营、财务、管理员登录管理后台', () => {
    expect(isAdminWebAllowedRole('operations')).toBe(true)
    expect(isAdminWebAllowedRole('finance')).toBe(true)
    expect(isAdminWebAllowedRole('admin')).toBe(true)
    expect(isAdminWebAllowedRole('customer')).toBe(false)
  })

  it('角色标签统一输出中文', () => {
    expect(getRoleLabel('operations')).toBe('运营')
    expect(getRoleLabel('warehouse')).toBe('仓库')
  })

  it('可构造演示模式登录会话', () => {
    expect(buildDemoSession('finance')).toMatchObject({
      roleCode: 'finance',
      roleLabel: '财务',
      clientType: 'admin_web',
      loginMode: 'demo',
    })
  })

  it('非法会话不会被恢复', () => {
    expect(parseStoredSession('{"foo":1}')).toBeNull()
    expect(
      parseStoredSession(
        JSON.stringify({
          userId: 'USER-1',
          roleCode: 'operations',
          roleLabel: '运营',
          companyType: 'operator_company',
          clientType: 'admin_web',
          loginMode: 'demo',
        }),
      ),
    ).toMatchObject({ roleCode: 'operations' })
  })
})
