function normalizeRoleCode(roleCode) {
  return String(roleCode || '').trim().toLowerCase();
}

function resolveHomePath(roleCode) {
  const normalized = normalizeRoleCode(roleCode);
  if (!normalized) {
    return '/pages/login/index';
  }
  return '/pages/todo/index';
}

function resolveHomeEntryLabel(roleCode) {
  return normalizeRoleCode(roleCode) ? '进入我的待办' : '进入登录入口';
}

module.exports = {
  resolveHomeEntryLabel,
  resolveHomePath,
};
