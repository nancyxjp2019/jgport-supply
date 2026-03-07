const { buildSupplierPurchasePageUrl } = require('./navigation');

const STATUS_PRIORITY_MAP = {
  已创建: 1,
  待供应商确认: 1,
  待付款校验: 3,
  可继续执行: 4,
  供应商已确认: 5,
  执行中: 6,
  已完成: 7,
};

const SUPPLIER_ATTACHMENT_TAG_OPTIONS = [
  { value: 'SUPPLIER_STAMPED_DOC', label: '盖章发货指令单' },
  { value: 'SUPPLIER_DELIVERY_RECEIPT', label: '供应商回单' },
];

function normalizeStatus(status) {
  return String(status || '').trim();
}

function resolvePurchaseOrderStatusClass(status) {
  const normalized = normalizeStatus(status);
  if (normalized === '待供应商确认') {
    return 'status-pill--error';
  }
  if (normalized === '已创建' || normalized === '待付款校验') {
    return 'status-pill--delayed';
  }
  if (['可继续执行', '执行中', '供应商已确认', '已完成'].includes(normalized)) {
    return 'status-pill--normal';
  }
  return 'status-pill--normal';
}

function buildSupplierSummaryCards(purchaseOrders) {
  const items = Array.isArray(purchaseOrders) ? purchaseOrders : [];
  const pendingConfirmCount = items.filter((item) => ['已创建', '待供应商确认'].includes(item.status)).length;
  const activeCount = items.filter((item) => ['可继续执行', '执行中'].includes(item.status)).length;
  const zeroPayCount = items.filter((item) => Boolean(item.zero_pay_exception_flag)).length;
  return [
    {
      key: 'pending-confirm',
      label: '待回看准备',
      value: pendingConfirmCount,
      desc: '优先核对发货准备信息与来源订单',
      className: 'todo-summary-card--danger',
    },
    {
      key: 'active',
      label: '可继续执行',
      value: activeCount,
      desc: '可继续跟踪付款校验后的执行进度',
      className: 'todo-summary-card--success',
    },
    {
      key: 'zero-pay',
      label: '零付款例外',
      value: zeroPayCount,
      desc: '仍需关注后续付款补录与执行推进',
      className: 'todo-summary-card--warning',
    },
  ];
}

function buildSupplierTodoItems(purchaseOrders) {
  return (Array.isArray(purchaseOrders) ? purchaseOrders : [])
    .slice()
    .sort((left, right) => {
      const priorityDiff = (STATUS_PRIORITY_MAP[normalizeStatus(left.status)] || 99) - (STATUS_PRIORITY_MAP[normalizeStatus(right.status)] || 99);
      if (priorityDiff !== 0) {
        return priorityDiff;
      }
      return String(right.created_at || '').localeCompare(String(left.created_at || ''));
    })
    .slice(0, 6)
    .map((item) => ({
      key: `supplier-purchase-${item.id}`,
      id: Number(item.id),
      orderNo: item.order_no,
      status: item.status,
      statusClass: resolvePurchaseOrderStatusClass(item.status),
      oilProductId: item.oil_product_id,
      qtyOrdered: item.qty_ordered,
      payableAmount: item.payable_amount,
      sourceSalesOrderNo: item.source_sales_order_no,
      createdAt: item.created_at || '',
      zeroPayExceptionFlag: Boolean(item.zero_pay_exception_flag),
      actionLabel: '查看详情',
      actionUrl: buildSupplierPurchasePageUrl({
        orderId: item.id,
        source: 'todo',
        sourceDetail: `已从待办定位到采购订单 ${item.order_no}。`,
      }),
    }));
}

function buildSupplierMessages(purchaseOrders) {
  const items = Array.isArray(purchaseOrders) ? purchaseOrders : [];
  const topItems = items
    .slice()
    .sort((left, right) => {
      const priorityDiff = (STATUS_PRIORITY_MAP[normalizeStatus(left.status)] || 99) - (STATUS_PRIORITY_MAP[normalizeStatus(right.status)] || 99);
      if (priorityDiff !== 0) {
        return priorityDiff;
      }
      return String(right.created_at || '').localeCompare(String(left.created_at || ''));
    })
    .slice(0, 4);

  if (!topItems.length) {
    return [
      {
        key: 'supplier-empty',
        level: 'info',
        title: '当前暂无采购进度消息',
        summary: '待财务审批生成采购订单后，系统会在这里聚合供应商首批进度提醒。',
        time: '',
        actionLabel: '查看采购进度',
        actionUrl: buildSupplierPurchasePageUrl({
          source: 'message',
          sourceDetail: '已从消息中心进入供应商采购进度页。',
        }),
      },
    ];
  }

  return topItems.map((item) => ({
    key: `supplier-${item.id}-${item.status}-${item.created_at || 'none'}`,
    level: resolveSupplierMessageLevel(item.status),
    title: `采购订单 ${item.order_no} ${item.status}`,
    summary: buildSupplierMessageSummary(item),
    time: item.created_at || '',
    actionLabel: '查看详情',
    actionUrl: buildSupplierPurchasePageUrl({
      orderId: item.id,
      source: 'message',
      sourceDetail: `已从消息定位到采购订单 ${item.order_no}。`,
    }),
  }));
}

function buildSupplierMessageSummary(item) {
  const status = normalizeStatus(item.status);
  if (status === '待供应商确认') {
    return `请先回看发货准备信息。来源销售订单 ${item.source_sales_order_no || '-'}。`;
  }
  if (status === '已创建') {
    return `新采购订单已生成，请先回看发货准备信息。来源销售订单 ${item.source_sales_order_no || '-'}。`;
  }
  if (status === '待付款校验') {
    return '当前等待付款校验结果，暂不开放供应商侧确认动作。';
  }
  if (status === '可继续执行') {
    return '付款校验已完成，可继续跟踪执行推进与附件入口开放情况。';
  }
  if (status === '执行中') {
    return '订单已进入执行中，请持续关注发运与仓储反馈。';
  }
  return '当前采购订单已进入首批可查看范围，可回看准备信息与后续入口。';
}

function resolveSupplierMessageLevel(status) {
  const normalized = normalizeStatus(status);
  if (normalized === '待供应商确认') {
    return 'warning';
  }
  if (normalized === '已创建') {
    return 'info';
  }
  if (normalized === '待付款校验') {
    return 'info';
  }
  if (normalized === '可继续执行' || normalized === '执行中') {
    return 'success';
  }
  return 'info';
}

function buildSupplierPreparationHints(order) {
  if (!order) {
    return [];
  }
  const hints = [
    `来源销售订单：${order.source_sales_order_no || order.source_sales_order_id || '-'}`,
    `当前状态：${order.status}`,
  ];
  if (Boolean(order.zero_pay_exception_flag)) {
    hints.push('当前命中零付款例外，仍需等待后续付款补录与执行推进。');
  } else {
    hints.push('当前已开放首批附件回传，可登记盖章发货指令单或供应商回单。');
  }
  if (Array.isArray(order.attachments) && order.attachments.length) {
    hints.push(`当前已登记附件 ${order.attachments.length} 份，可继续补充回单留痕。`);
  }
  return hints;
}

function getSupplierAttachmentTagOptions() {
  return SUPPLIER_ATTACHMENT_TAG_OPTIONS.map((item) => ({ ...item }));
}

function resolveSupplierAttachmentTagLabel(bizTag) {
  const matched = SUPPLIER_ATTACHMENT_TAG_OPTIONS.find((item) => item.value === String(bizTag || '').trim().toUpperCase());
  return matched ? matched.label : '未识别附件';
}

function buildSupplierAttachmentItems(items) {
  return (Array.isArray(items) ? items : []).map((item) => ({
    ...item,
    bizTagLabel: resolveSupplierAttachmentTagLabel(item.biz_tag),
  }));
}

module.exports = {
  buildSupplierAttachmentItems,
  buildSupplierMessages,
  buildSupplierPreparationHints,
  buildSupplierSummaryCards,
  buildSupplierTodoItems,
  getSupplierAttachmentTagOptions,
  resolvePurchaseOrderStatusClass,
  resolveSupplierAttachmentTagLabel,
};
