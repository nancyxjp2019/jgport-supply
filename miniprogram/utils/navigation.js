function normalizeRoleCode(roleCode) {
  return String(roleCode || '').trim().toLowerCase();
}

function resolveHomePath(roleCode) {
  return normalizeRoleCode(roleCode) === 'warehouse' ? '/pages/exec/index' : '/pages/report/index';
}

function resolveHomeEntryLabel(roleCode) {
  return normalizeRoleCode(roleCode) === 'warehouse' ? '进入仓库执行回执' : '进入经营快报';
}

module.exports = {
  resolveHomeEntryLabel,
  resolveHomePath,
};
