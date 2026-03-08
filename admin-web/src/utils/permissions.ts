export type AdminActionCode =
  | 'org.manage'
  | 'contracts.view'
  | 'contracts.write'
  | 'contracts.approve'
  | 'orders.ops.approve'
  | 'orders.finance.approve'
  | 'funds.operate'
  | 'funds.reconcile.operate'
  | 'reports.multi_dim.export'
  | 'reports.summary.recompute.view'
  | 'reports.summary.recompute'

const ROLE_ACTIONS: Record<string, ReadonlyArray<AdminActionCode>> = {
  operations: ['contracts.view', 'orders.ops.approve', 'reports.summary.recompute.view'],
  finance: [
    'contracts.view',
    'contracts.write',
    'contracts.approve',
    'orders.finance.approve',
    'funds.operate',
    'funds.reconcile.operate',
    'reports.multi_dim.export',
    'reports.summary.recompute.view',
    'reports.summary.recompute',
  ],
  admin: [
    'org.manage',
    'contracts.view',
    'contracts.write',
    'contracts.approve',
    'orders.ops.approve',
    'orders.finance.approve',
    'funds.operate',
    'funds.reconcile.operate',
    'reports.multi_dim.export',
    'reports.summary.recompute.view',
    'reports.summary.recompute',
  ],
}

export function canRoleExecuteAction(roleCode: string | null | undefined, action: AdminActionCode): boolean {
  if (!roleCode) {
    return false
  }
  return (ROLE_ACTIONS[roleCode] || []).includes(action)
}
