const {
  abnormalCloseSalesOrder,
  financeApproveSalesOrder,
  getSalesOrderDetail,
  getSalesOrderLogs,
  getSalesOrderProgress,
  operatorApproveSalesOrder,
  rejectSalesOrder,
} = require('../../../utils/api');
const { chooseAndUploadFile, openRemoteFile } = require('../../../utils/file');
const { formatDate, formatDateTime, formatMoney, formatNumber } = require('../../../utils/format');
const { toGenericStatusText, toProgressStatusText, toSalesOrderStatusText } = require('../../../utils/status');

function normalizeTankType(value) {
  const text = String(value || '').trim();
  if (!text) {
    return '';
  }
  return {
    单仓: '单枪',
    双仓: '双枪',
    单枪: '单枪',
    双枪: '双枪',
  }[text] || text;
}

function getContractLabel(role) {
  return role === 'CUSTOMER' ? '合同' : '销售合同';
}

function getPageTitle(role) {
  return role === 'CUSTOMER' ? '订单详情' : '销售订单详情';
}

function buildListStatusText(status) {
  return toSalesOrderStatusText(status);
}

function buildMoneyText(value) {
  const text = formatMoney(value);
  return text === '-' ? '-' : `${text} 元`;
}

function buildRemoteFileName(fileName, fileKey, fallbackName) {
  const normalizedName = String(fileName || '').trim();
  if (normalizedName) {
    return normalizedName;
  }
  const normalizedKey = String(fileKey || '').trim();
  if (normalizedKey) {
    const keyName = normalizedKey.split('/').pop() || normalizedKey;
    if (keyName) {
      return keyName;
    }
  }
  return String(fallbackName || '').trim();
}

Page({
  data: {
    orderId: 0,
    role: '',
    detail: null,
    progressNodes: [],
    logs: [],
    paymentVouchers: [],
    loading: false,
    financeReceivedAmount: '',
    financeReceiptFileKey: '',
    financeReceiptFileName: '',
    adminReason: '',
    contractLabel: '销售合同',
  },

  onLoad(options) {
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '');
    wx.setNavigationBarTitle({ title: getPageTitle(role) });
    this.setData({
      orderId: Number(options.id || 0),
      role,
      contractLabel: getContractLabel(role),
    });
  },

  onShow() {
    if (this.skipNextOnShowReload) {
      this.skipNextOnShowReload = false;
      return;
    }
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    const role = String(user.role || '');
    this.setData({
      role,
      contractLabel: getContractLabel(role),
    });
    wx.setNavigationBarTitle({ title: getPageTitle(role) });
    this.loadData();
  },

  async loadData() {
    if (!this.data.orderId) {
      return;
    }
    this.setData({ loading: true });
    try {
      const [detailRes, progressRes] = await Promise.all([
        getSalesOrderDetail(this.data.orderId),
        getSalesOrderProgress(this.data.orderId),
      ]);
      const detailData = detailRes.data || {};
      const draftFinanceReceivedAmount = String(this.data.financeReceivedAmount || '').trim();
      const draftFinanceReceiptFileKey = String(this.data.financeReceiptFileKey || '').trim();
      const draftFinanceReceiptFileName = String(this.data.financeReceiptFileName || '').trim();
      const receiptFileKey = String(detailData.customer_payment_receipt_file_key || '').trim();
      const financePending = this.data.role === 'FINANCE' && detailData.status === 'OPERATOR_APPROVED';
      let logs = [];
      if (['OPERATOR', 'FINANCE', 'ADMIN'].includes(this.data.role)) {
        try {
          const logRes = await getSalesOrderLogs(this.data.orderId);
          logs = logRes.data || [];
        } catch (_error) {
          logs = [];
        }
      }
      this.setData({
        detail: {
          ...detailData,
          buyer_company_name: detailData.buyer_company_name || detailData.customer_company_name || '',
          seller_company_name: detailData.seller_company_name || '',
          customer_payment_receipt_file_name: buildRemoteFileName(
            detailData.customer_payment_receipt_file_name,
            detailData.customer_payment_receipt_file_key,
            `${detailData.sales_order_no || '销售订单'}-收款凭证.pdf`,
          ),
          transport_snapshot: {
            ...(detailData.transport_snapshot || {}),
            tank_type: normalizeTankType(detailData.transport_snapshot && detailData.transport_snapshot.tank_type),
            with_pump_text:
              detailData.transport_snapshot && detailData.transport_snapshot.with_pump === true
                ? '带泵'
                : '不带泵',
          },
          status_text: toSalesOrderStatusText(detailData.status),
          order_date_text: formatDate(detailData.order_date),
          created_at_text: formatDateTime(detailData.created_at),
          qty_text: formatNumber(detailData.qty_ton, 4),
          unit_price_tax_included_text: buildMoneyText(detailData.unit_price_tax_included),
          amount_tax_included_text: buildMoneyText(detailData.amount_tax_included),
          amount_tax_excluded_text: buildMoneyText(detailData.amount_tax_excluded),
          tax_amount_text: buildMoneyText(detailData.tax_amount),
          received_amount_text: buildMoneyText(detailData.received_amount),
        },
        progressNodes: ((progressRes.data && progressRes.data.nodes) || []).map((item) => ({
          ...item,
          status_text: toProgressStatusText(item.status),
        })),
        logs: logs.map((item) => ({
          ...item,
          before_status_text: toGenericStatusText(item.before_status),
          after_status_text: toGenericStatusText(item.after_status),
        })),
        paymentVouchers: ((detailData && detailData.transport_file_urls) || []).map((url, index) => {
          const fileKey = ((detailData && detailData.transport_file_keys) || [])[index] || `付款凭证${index + 1}`;
          const fileName = ((detailData && detailData.transport_file_names) || [])[index];
          return {
            url,
            name: buildRemoteFileName(fileName, fileKey, `付款凭证${index + 1}`),
          };
        }),
        financeReceivedAmount:
          detailData.received_amount !== null && detailData.received_amount !== undefined
            ? formatMoney(detailData.received_amount)
            : (financePending ? draftFinanceReceivedAmount : ''),
        financeReceiptFileKey: receiptFileKey || (financePending ? draftFinanceReceiptFileKey : ''),
        financeReceiptFileName:
          buildRemoteFileName(detailData.customer_payment_receipt_file_name, receiptFileKey, '')
          || (financePending ? draftFinanceReceiptFileName : ''),
      });
    } catch (error) {
      wx.showToast({ title: error.message || '加载失败', icon: 'none' });
    }
    this.setData({ loading: false });
  },

  onFinanceAmountInput(e) {
    this.setData({ financeReceivedAmount: String(e.detail.value || '').trim() });
  },

  onAdminReasonInput(e) {
    this.setData({ adminReason: String(e.detail.value || '').trim() });
  },

  async onUploadFinanceReceipt() {
    try {
      this.skipNextOnShowReload = true;
      const uploaded = await chooseAndUploadFile('receipt');
      this.setData({
        financeReceiptFileKey: uploaded.file_key,
        financeReceiptFileName: uploaded.original_filename || uploaded.file_key,
      });
    } catch (error) {
      this.skipNextOnShowReload = false;
      wx.showToast({ title: error.message || '上传失败', icon: 'none' });
    }
  },

  async onOperatorApprove() {
    try {
      const res = await operatorApproveSalesOrder(this.data.orderId);
      wx.showToast({ title: '已审核通过', icon: 'success' });
      await this.syncListPageAfterOperatorApprove(res.data);
      wx.navigateBack();
    } catch (error) {
      wx.showToast({ title: error.message || '操作失败', icon: 'none' });
    }
  },

  async onFinanceApprove() {
    if (!this.data.financeReceiptFileKey) {
      wx.showToast({ title: '请先上传收款凭证', icon: 'none' });
      return;
    }
    try {
      await financeApproveSalesOrder(this.data.orderId, {
        action: 'approve',
        received_amount: Number(String(this.data.financeReceivedAmount || '').replace(/,/g, '')) || 0,
        customer_payment_receipt_file_key: this.data.financeReceiptFileKey,
      });
      wx.showToast({ title: '财务审核完成', icon: 'success' });
      this.loadData();
    } catch (error) {
      wx.showToast({ title: error.message || '操作失败', icon: 'none' });
    }
  },

  async onReject() {
    if (!this.data.adminReason) {
      wx.showToast({ title: '请输入驳回原因', icon: 'none' });
      return;
    }
    // 驳回为不可撤销终态操作，需要二次确认
    const confirmed = await new Promise((resolve) => {
      wx.showModal({
        title: '确认驳回订单',
        content: `驳回原因：${this.data.adminReason}\n\n驳回后订单进入终态，此操作不可撤销。`,
        confirmText: '确认驳回',
        cancelText: '取消',
        success: (res) => resolve(res.confirm),
      });
    });
    if (!confirmed) return;
    try {
      await rejectSalesOrder(this.data.orderId, this.data.adminReason);
      wx.showToast({ title: '订单已驳回', icon: 'success' });
      this.loadData();
    } catch (error) {
      wx.showToast({ title: error.message || '操作失败', icon: 'none' });
    }
  },

  async onAbnormalClose() {
    if (!this.data.adminReason) {
      wx.showToast({ title: '请输入异常关闭原因', icon: 'none' });
      return;
    }
    // 异常关闭为不可撤销终态操作，需要二次确认
    const confirmed = await new Promise((resolve) => {
      wx.showModal({
        title: '确认异常关闭',
        content: `关闭原因：${this.data.adminReason}\n\n此操作不可撤销，请确认。`,
        confirmText: '确认关闭',
        cancelText: '取消',
        success: (res) => resolve(res.confirm),
      });
    });
    if (!confirmed) return;
    try {
      await abnormalCloseSalesOrder(this.data.orderId, this.data.adminReason);
      wx.showToast({ title: '订单已异常关闭', icon: 'success' });
      this.loadData();
    } catch (error) {
      wx.showToast({ title: error.message || '操作失败', icon: 'none' });
    }
  },

  async onOpenReceipt() {
    const url = this.data.detail && this.data.detail.customer_payment_receipt_file_url;
    const fileName = this.data.detail && this.data.detail.customer_payment_receipt_file_name;
    if (!url) {
      wx.showToast({ title: '暂无收款凭证', icon: 'none' });
      return;
    }
    try {
      await openRemoteFile(url, { fileName });
    } catch (error) {
      wx.showToast({ title: error.message || '打开失败', icon: 'none' });
    }
  },

  async onOpenRemoteFile(e) {
    const url = e.currentTarget.dataset.url;
    const fileName = String(e.currentTarget.dataset.name || '').trim();
    if (!url) {
      wx.showToast({ title: '暂无文件', icon: 'none' });
      return;
    }
    try {
      await openRemoteFile(url, { fileName });
    } catch (error) {
      wx.showToast({ title: error.message || '打开失败', icon: 'none' });
    }
  },

  onOpenPurchaseOrder() {
    const purchaseOrderId = this.data.detail && this.data.detail.purchase_order_id;
    if (!purchaseOrderId) {
      return;
    }
    wx.navigateTo({ url: `/pages/purchase-orders/detail/index?id=${purchaseOrderId}` });
  },

  async syncListPageAfterOperatorApprove(detail) {
    const pages = getCurrentPages();
    const previousPage = pages.length > 1 ? pages[pages.length - 2] : null;
    if (!previousPage || previousPage.route !== 'pages/sales-orders/list/index') {
      return;
    }

    const nextItems = (previousPage.data.items || [])
      .map((item) => {
        if (Number(item.id) !== Number(detail.id)) {
          return item;
        }
        return {
          ...item,
          status: detail.status,
          status_text: buildListStatusText(detail.status),
          reserved_qty_ton: detail.reserved_qty_ton,
          actual_outbound_qty_ton: detail.actual_outbound_qty_ton,
        };
      })
      .filter((item) => !(previousPage.data.pendingOnly && Number(item.id) === Number(detail.id)));

    previousPage.setData({ items: nextItems });
    if (typeof previousPage.loadData === 'function') {
      await previousPage.loadData();
    }
  },
});
