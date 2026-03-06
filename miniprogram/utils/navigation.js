function normalizeRoleCode(roleCode) {
  return String(roleCode || '').trim().toLowerCase();
}

function normalizeText(value) {
  return String(value || '').trim();
}

function buildPageUrl(path, query) {
  const basePath = normalizeText(path) || '/pages/todo/index';
  const entries = Object.entries(query || {})
    .map(([key, value]) => [normalizeText(key), normalizeText(value)])
    .filter(([key, value]) => key && value);
  if (!entries.length) {
    return basePath;
  }
  const queryText = entries.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`).join('&');
  return `${basePath}?${queryText}`;
}

function buildOrderPageUrl(options) {
  const sourceDetail = normalizeText(options && options.sourceDetail);
  const payload = {
    tab: normalizeText(options && options.tab) || 'query',
    status: normalizeText(options && options.status),
    editOrderId: normalizeText(options && options.editOrderId),
    source: normalizeText(options && options.source),
    sourceDetail,
  };
  return buildPageUrl('/pages/order/index', payload);
}

function buildReportPageUrl(options) {
  return buildPageUrl('/pages/report/index', {
    focusAbnormal: normalizeText(options && options.focusAbnormal),
    source: normalizeText(options && options.source),
    sourceDetail: normalizeText(options && options.sourceDetail),
  });
}

function buildExecPageUrl(options) {
  return buildPageUrl('/pages/exec/index', {
    mode: normalizeText(options && options.mode) || 'system',
    source: normalizeText(options && options.source),
    sourceDetail: normalizeText(options && options.sourceDetail),
  });
}

function resolveEntrySourceMeta(options) {
  const source = normalizeText(options && options.source);
  const sourceDetail = normalizeText(options && options.sourceDetail);
  if (source === 'message') {
    return {
      sourceText: '当前通过消息中心进入该页面。',
      sourceDetailText: sourceDetail || '已按消息提醒为你定位对应业务入口。',
    };
  }
  if (source === 'todo') {
    return {
      sourceText: '当前通过我的待办进入该页面。',
      sourceDetailText: sourceDetail || '可继续处理待办摘要对应的业务动作。',
    };
  }
  return {
    sourceText: '',
    sourceDetailText: '',
  };
}

function resolveReportFocusKey(value) {
  const normalized = normalizeText(value);
  if (['pending', 'failed', 'qtydone'].includes(normalized)) {
    return normalized;
  }
  return '';
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
  buildExecPageUrl,
  buildOrderPageUrl,
  buildPageUrl,
  buildReportPageUrl,
  resolveHomeEntryLabel,
  resolveHomePath,
  resolveEntrySourceMeta,
  resolveReportFocusKey,
};
