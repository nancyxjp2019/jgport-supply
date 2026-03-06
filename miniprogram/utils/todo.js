const OPERATOR_ROLE_CODES = new Set(['operations', 'finance', 'admin']);
const CUSTOMER_PENDING_STATUSES = ['草稿', '驳回', '待运营审批', '待财务审批'];

function normalizeRoleCode(roleCode) {
  return String(roleCode || '').trim().toLowerCase();
}

function resolveTodoMode(roleCode) {
  const normalized = normalizeRoleCode(roleCode);
  if (normalized === 'customer') {
    return 'customer';
  }
  if (OPERATOR_ROLE_CODES.has(normalized)) {
    return 'operator';
  }
  if (normalized === 'warehouse') {
    return 'warehouse';
  }
  if (normalized === 'supplier') {
    return 'supplier';
  }
  return 'unknown';
}

function buildCustomerSummaryCards(orders) {
  const items = Array.isArray(orders) ? orders : [];
  const draftCount = items.filter((item) => item.status === '草稿').length;
  const pendingCount = items.filter((item) => ['待运营审批', '待财务审批'].includes(item.status)).length;
  const rejectedCount = items.filter((item) => item.status === '驳回').length;
  return [
    {
      key: 'draft',
      label: '草稿待提交',
      value: draftCount,
      desc: '可继续补充并提交审批',
      className: 'todo-summary-card--info',
    },
    {
      key: 'pending',
      label: '审批处理中',
      value: pendingCount,
      desc: '等待运营或财务处理',
      className: 'todo-summary-card--pending',
    },
    {
      key: 'rejected',
      label: '驳回待修改',
      value: rejectedCount,
      desc: '请尽快补充后重新提交',
      className: 'todo-summary-card--danger',
    },
  ];
}

function buildCustomerTodoItems(orders) {
  const items = Array.isArray(orders) ? orders : [];
  const priorityMap = {
    驳回: 1,
    草稿: 2,
    待运营审批: 3,
    待财务审批: 4,
  };
  return items
    .filter((item) => CUSTOMER_PENDING_STATUSES.includes(item.status))
    .sort((left, right) => {
      const priorityDiff = (priorityMap[left.status] || 99) - (priorityMap[right.status] || 99);
      if (priorityDiff !== 0) {
        return priorityDiff;
      }
      return String(right.created_at || '').localeCompare(String(left.created_at || ''));
    })
    .slice(0, 6)
    .map((item) => ({
      key: `customer-order-${item.id}`,
      id: Number(item.id),
      orderNo: item.order_no,
      contractNo: item.sales_contract_no,
      status: item.status,
      statusClass: resolveCustomerStatusClass(item.status),
      oilProductId: item.oil_product_id,
      qtyOrdered: item.qty_ordered,
      submittedAt: item.submitted_at || '',
      createdAt: item.created_at || '',
      actionLabel: ['草稿', '驳回'].includes(item.status) ? '继续处理' : '查看进度',
      actionUrl: ['草稿', '驳回'].includes(item.status)
        ? `/pages/order/index?tab=query&editOrderId=${item.id}`
        : '/pages/order/index?tab=query',
    }));
}

function resolveCustomerStatusClass(status) {
  if (status === '草稿') {
    return 'status-pill--normal';
  }
  if (status === '驳回') {
    return 'status-pill--error';
  }
  return 'status-pill--delayed';
}

function buildOperatorSummaryCards(overview) {
  return [
    {
      key: 'pending',
      label: '待补录金额',
      value: Number(overview.pending_supplement_count || 0),
      desc: '优先补录金额与凭证',
      className: 'todo-summary-card--pending',
    },
    {
      key: 'failed',
      label: '校验失败',
      value: Number(overview.validation_failed_count || 0),
      desc: '存在阻断生效的异常单据',
      className: 'todo-summary-card--danger',
    },
    {
      key: 'qtydone',
      label: '数量完成未关闭',
      value: Number(overview.qty_done_not_closed_count || 0),
      desc: '请核对金额闭环与关闭条件',
      className: 'todo-summary-card--warning',
    },
  ];
}

function buildOperatorTodoItems(overview) {
  return [
    {
      key: 'pending',
      title: '待补录金额',
      value: Number(overview.pending_supplement_count || 0),
      tip: '当前仍需财务补录金额或凭证，详细处理请使用管理后台。',
      actionLabel: '查看经营快报',
    },
    {
      key: 'failed',
      title: '校验失败',
      value: Number(overview.validation_failed_count || 0),
      tip: '存在阈值或流程阻断异常，建议优先核对对应单据。',
      actionLabel: '查看经营快报',
    },
    {
      key: 'qtydone',
      title: '数量履约完成未关闭',
      value: Number(overview.qty_done_not_closed_count || 0),
      tip: '数量已完成但金额闭环未收口，请在后台继续处理。',
      actionLabel: '查看经营快报',
    },
  ].filter((item) => item.value > 0);
}

function buildWarehouseQuickActions() {
  return [
    {
      key: 'system',
      title: '正常回执',
      desc: '按仓库回执号提交正常执行结果。',
      url: '/pages/exec/index?mode=system',
      actionLabel: '去处理',
    },
    {
      key: 'manual',
      title: '手工补录',
      desc: '异常场景下补录执行回执并立即生效。',
      url: '/pages/exec/index?mode=manual',
      actionLabel: '去处理',
    },
  ];
}

function buildWarehouseSummaryCards() {
  return [
    {
      key: 'exec',
      label: '执行入口',
      value: '已开放',
      desc: '支持正常回执和手工补录',
      className: 'todo-summary-card--success',
    },
  ];
}

module.exports = {
  buildCustomerSummaryCards,
  buildCustomerTodoItems,
  buildOperatorSummaryCards,
  buildOperatorTodoItems,
  buildWarehouseQuickActions,
  buildWarehouseSummaryCards,
  resolveTodoMode,
};
