import { describe, expect, it } from 'vitest'

import { canRoleExecuteAction } from './permissions'

describe('permissions utils', () => {
  it('运营仅可执行运营审批动作', () => {
    expect(canRoleExecuteAction('operations', 'contracts.view')).toBe(true)
    expect(canRoleExecuteAction('operations', 'orders.ops.approve')).toBe(true)
    expect(canRoleExecuteAction('operations', 'reports.summary.recompute.view')).toBe(true)
    expect(canRoleExecuteAction('operations', 'contracts.write')).toBe(false)
    expect(canRoleExecuteAction('operations', 'contracts.approve')).toBe(false)
    expect(canRoleExecuteAction('operations', 'reports.summary.recompute')).toBe(false)
    expect(canRoleExecuteAction('operations', 'orders.finance.approve')).toBe(false)
    expect(canRoleExecuteAction('operations', 'funds.operate')).toBe(false)
  })

  it('财务可执行资金与财务审批动作', () => {
    expect(canRoleExecuteAction('finance', 'contracts.view')).toBe(true)
    expect(canRoleExecuteAction('finance', 'contracts.write')).toBe(true)
    expect(canRoleExecuteAction('finance', 'contracts.approve')).toBe(true)
    expect(canRoleExecuteAction('finance', 'orders.finance.approve')).toBe(true)
    expect(canRoleExecuteAction('finance', 'funds.operate')).toBe(true)
    expect(canRoleExecuteAction('finance', 'funds.reconcile.operate')).toBe(true)
    expect(canRoleExecuteAction('finance', 'reports.summary.recompute.view')).toBe(true)
    expect(canRoleExecuteAction('finance', 'reports.summary.recompute')).toBe(true)
    expect(canRoleExecuteAction('finance', 'orders.ops.approve')).toBe(false)
  })

  it('管理员具备首批全部按钮权限', () => {
    expect(canRoleExecuteAction('admin', 'contracts.view')).toBe(true)
    expect(canRoleExecuteAction('admin', 'contracts.write')).toBe(true)
    expect(canRoleExecuteAction('admin', 'contracts.approve')).toBe(true)
    expect(canRoleExecuteAction('admin', 'orders.ops.approve')).toBe(true)
    expect(canRoleExecuteAction('admin', 'orders.finance.approve')).toBe(true)
    expect(canRoleExecuteAction('admin', 'reports.multi_dim.export')).toBe(true)
    expect(canRoleExecuteAction('admin', 'reports.summary.recompute.view')).toBe(true)
    expect(canRoleExecuteAction('admin', 'reports.summary.recompute')).toBe(true)
  })
})
