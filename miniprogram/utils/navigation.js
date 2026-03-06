function normalizeRoleCode(roleCode) {
  return String(roleCode || '').trim().toLowerCase();
}

function resolveHomePath(roleCode) {
  const normalized = normalizeRoleCode(roleCode);
  if (normalized === 'warehouse') {
    return '/pages/exec/index';
  }
  if (normalized === 'customer') {
    return '/pages/order/index';
  }
  return '/pages/report/index';
}

function resolveHomeEntryLabel(roleCode) {
  const normalized = normalizeRoleCode(roleCode);
  if (normalized === 'warehouse') {
    return '进入仓库执行回执';
  }
  if (normalized === 'customer') {
    return '进入订单发起与查询';
  }
  return '进入经营快报';
}

module.exports = {
  resolveHomeEntryLabel,
  resolveHomePath,
};
