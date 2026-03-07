export type AdminActionCode =
  | 'orders.ops.approve'
  | 'orders.finance.approve'
  | 'funds.operate'
  | 'funds.reconcile.operate'
  | 'reports.multi_dim.export'

const ROLE_ACTIONS: Record<string, ReadonlyArray<AdminActionCode>> = {
  operations: ['orders.ops.approve'],
  finance: [
    'orders.finance.approve',
    'funds.operate',
    'funds.reconcile.operate',
    'reports.multi_dim.export',
  ],
  admin: [
    'orders.ops.approve',
    'orders.finance.approve',
    'funds.operate',
    'funds.reconcile.operate',
    'reports.multi_dim.export',
  ],
}

export function canRoleExecuteAction(roleCode: string | null | undefined, action: AdminActionCode): boolean {
  if (!roleCode) {
    return false
  }
  return (ROLE_ACTIONS[roleCode] || []).includes(action)
}
