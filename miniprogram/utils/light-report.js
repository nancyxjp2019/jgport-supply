const ALLOWED_ROLE_CODES = new Set(['operations', 'finance', 'admin']);

const ROLE_LABEL_MAP = Object.freeze({
  operations: '运营',
  finance: '财务',
  admin: '管理员',
  customer: '客户',
  supplier: '供应商',
  warehouse: '仓库',
});

function normalizeRoleCode(roleCode) {
  return String(roleCode || '').trim().toLowerCase();
}

function canViewLightReport(roleCode) {
  return ALLOWED_ROLE_CODES.has(normalizeRoleCode(roleCode));
}

function getRoleLabel(roleCode) {
  return ROLE_LABEL_MAP[normalizeRoleCode(roleCode)] || '未知角色';
}

function resolveOverviewStatusText(slaStatus) {
  return slaStatus === '延迟' ? '数据更新中，请稍后再试' : '数据已更新';
}

function resolveStatusClass(slaStatus) {
  return slaStatus === '延迟' ? 'status-pill--delayed' : 'status-pill--normal';
}

function buildMetricCards(overview, formatters) {
  return [
    {
      key: 'receipt',
      label: '当日实收',
      value: `¥${formatters.formatMoney(overview.actual_receipt_today)}`,
      desc: '按上海自然日统计',
      className: 'metric-card--receipt',
    },
    {
      key: 'payment',
      label: '当日实付',
      value: `¥${formatters.formatMoney(overview.actual_payment_today)}`,
      desc: '已确认净额口径',
      className: 'metric-card--payment',
    },
    {
      key: 'inbound',
      label: '当日入库量',
      value: formatters.formatQty(overview.inbound_qty_today),
      desc: '已过账入库合计',
      className: 'metric-card--inbound',
    },
    {
      key: 'outbound',
      label: '当日出库量',
      value: formatters.formatQty(overview.outbound_qty_today),
      desc: '已过账出库合计',
      className: 'metric-card--outbound',
    },
  ];
}

function buildAbnormalItems(overview) {
  return [
    {
      key: 'pending',
      label: '待补录金额',
      value: Number(overview.pending_supplement_count || 0),
      className: 'abnormal-pill--pending',
      tip: '请财务尽快补录金额或凭证',
    },
    {
      key: 'failed',
      label: '校验失败',
      value: Number(overview.validation_failed_count || 0),
      className: 'abnormal-pill--failed',
      tip: '请优先处理阻断生效的异常单据',
    },
    {
      key: 'qtydone',
      label: '数量履约完成未关闭',
      value: Number(overview.qty_done_not_closed_count || 0),
      className: 'abnormal-pill--qtydone',
      tip: '请核对金额闭环后完成合同关闭',
    },
  ];
}

function isOverviewEmpty(overview) {
  if (!overview) {
    return true;
  }
  return [
    Number(overview.actual_receipt_today || 0),
    Number(overview.actual_payment_today || 0),
    Number(overview.inbound_qty_today || 0),
    Number(overview.outbound_qty_today || 0),
    Number(overview.abnormal_count || 0),
  ].every((value) => value === 0);
}

module.exports = {
  buildAbnormalItems,
  buildMetricCards,
  canViewLightReport,
  getRoleLabel,
  isOverviewEmpty,
  resolveOverviewStatusText,
  resolveStatusClass,
};
