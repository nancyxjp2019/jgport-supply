const {
  abnormalClosePurchaseOrder,
  getDeliveryTemplates,
  getPurchaseContractOptions,
  getPurchaseOrderDetail,
  getPurchaseOrderLogs,
  submitPurchaseOrder,
  supplierReviewPurchaseOrder,
  warehouseOutboundPurchaseOrder,
} = require('../../../utils/api');
const { chooseAndUploadFile, openRemoteFile } = require('../../../utils/file');
const { formatDate, formatDateTime, formatMoney, formatNumber } = require('../../../utils/format');
const { toGenericStatusText, toPurchaseOrderStatusText } = require('../../../utils/status');

function buildMoneyText(value) {
  const text = formatMoney(value);
  return text === '-' ? '-' : `${text} 元`;
}

function parseQtyToUnits(value) {
  const text = String(value || '').trim();
  if (!text || !/^\d+(\.\d{0,4})?$/.test(text)) return null;
  const [integerPart, decimalPart = ''] = text.split('.');
  return Number(integerPart) * 10000 + Number((decimalPart + '0000').slice(0, 4));
}

function formatQtyUnits(units) {
  const integerPart = Math.floor(units / 10000);
  const decimalText = String(units % 10000).padStart(4, '0').replace(/0+$/, '');
  return decimalText ? `${integerPart}.${decimalText}` : `${integerPart}`;
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

function buildOutboundRuleText(orderQty) {
  const orderUnits = parseQtyToUnits(orderQty);
  if (orderUnits === null) {
    return '实际出库数量不得低于订单数量，且不得超过订单数量的110%';
  }
  const maxUnits = Math.floor((orderUnits * 11) / 10);
  return `实际出库数量不得低于订单数量，且不得超过 ${formatQtyUnits(maxUnits)} 吨`;
}

function validateOutboundQty(outboundQty, orderQty) {
  const outboundUnits = parseQtyToUnits(outboundQty);
  if (outboundUnits === null) {
    return '请输入正确的实际出库数量，最多保留4位小数';
  }
  const orderUnits = parseQtyToUnits(orderQty);
  if (orderUnits === null) return '';
  if (outboundUnits < orderUnits) {
    return '实际出库数量不得低于订单数量';
  }
  const maxUnits = Math.floor((orderUnits * 11) / 10);
  if (outboundUnits > maxUnits) {
    return `实际出库数量不得超过订单数量的110%（最大 ${formatQtyUnits(maxUnits)} 吨）`;
  }
  return '';
}

// 规范化单双枪文案（兼容旧值）
function normalizeTankType(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  return { 单仓: '单枪', 双仓: '双枪', 单枪: '单枪', 双枪: '双枪' }[text] || text;
}

// 构建运输快照（由后端关联销售订单携带，字段存在则处理，否则返回 null）
function buildTransportSnapshot(raw) {
  if (!raw) return null;
  return {
    ...raw,
    tank_type: normalizeTankType(raw.tank_type),
    with_pump_text: raw.with_pump === true ? '带泵' : '不带泵',
  };
}

Page({
  data: {
    orderId: 0,
    role: '',
    detail: null,
    logs: [],
    purchaseContractOptions: [],
    deliveryTemplates: [],
    selectedPurchaseContractIndex: 0,
    selectedDeliveryTemplateIndex: 0,
    selectedPurchaseContract: null,
    selectedDeliveryTemplate: null,
    confirmAcknowledged: false,
    supplierPaymentVouchers: [],
    supplierDeliveryDoc: null,
    outboundDoc: null,
    outboundQty: '',
    outboundRuleText: '',
    adminReason: '',
  },

  onLoad(options) {
    this.setData({ orderId: Number(options.id || 0) });
  },

  onShow() {
    if (this.skipNextOnShowReload) {
      this.skipNextOnShowReload = false;
      return;
    }
    const app = getApp();
    const user = app.globalData.user || wx.getStorageSync('user') || {};
    this.setData({ role: String(user.role || '') });
    this.loadData();
  },

  async loadData() {
    try {
      const detailRes = await getPurchaseOrderDetail(this.data.orderId);
      let logs = [];
      if (['FINANCE', 'ADMIN'].includes(this.data.role)) {
        try {
          const logRes = await getPurchaseOrderLogs(this.data.orderId);
          logs = logRes.data || [];
        } catch (_error) {
          logs = [];
        }
      }
      const detail = {
        ...detailRes.data,
        buyer_company_name: detailRes.data.buyer_company_name || '',
        seller_company_name: detailRes.data.seller_company_name || detailRes.data.supplier_company_name || '',
        delivery_instruction_pdf_file_name: buildRemoteFileName(
          detailRes.data.delivery_instruction_pdf_file_name,
          detailRes.data.delivery_instruction_pdf_file_key,
          `${detailRes.data.purchase_order_no || '采购订单'}-发货指令单.pdf`,
        ),
        supplier_delivery_doc_file_name: buildRemoteFileName(
          detailRes.data.supplier_delivery_doc_file_name,
          detailRes.data.supplier_delivery_doc_file_key,
          `${detailRes.data.purchase_order_no || '采购订单'}-盖章发货指令单`,
        ),
        outbound_doc_file_name: buildRemoteFileName(
          detailRes.data.outbound_doc_file_name,
          detailRes.data.outbound_doc_file_key,
          `${detailRes.data.purchase_order_no || '采购订单'}-出库单`,
        ),
        status_text: toPurchaseOrderStatusText(detailRes.data.status),
        order_date_text: formatDate(detailRes.data.order_date),
        qty_text: formatNumber(detailRes.data.qty_ton, 4),
        unit_price_tax_included_text: buildMoneyText(detailRes.data.unit_price_tax_included),
        amount_tax_included_text: buildMoneyText(detailRes.data.amount_tax_included),
        amount_tax_excluded_text: buildMoneyText(detailRes.data.amount_tax_excluded),
        tax_amount_text: buildMoneyText(detailRes.data.tax_amount),
        created_at_text: formatDateTime(detailRes.data.created_at),
        // 运输快照：后端在采购订单详情中携带关联销售订单的运输信息，仓库角色据此核对车辆与司机
        transport_snapshot: buildTransportSnapshot(detailRes.data.transport_snapshot),
      };
      this.setData({
        detail,
        logs: logs.map((item) => ({
          ...item,
          before_status_text: toGenericStatusText(item.before_status),
          after_status_text: toGenericStatusText(item.after_status),
        })),
        outboundQty: detail.actual_outbound_qty_ton ? `${detail.actual_outbound_qty_ton}` : `${detail.qty_ton}`,
        outboundRuleText: buildOutboundRuleText(detail.qty_ton),
      });
      if (this.data.role === 'FINANCE' && detail.status === 'PENDING_SUBMIT') {
        await this.loadSubmitOptions(detail);
      }
    } catch (error) {
      wx.showToast({ title: error.message || '加载失败', icon: 'none' });
    }
  },

  async loadSubmitOptions(detail) {
    try {
      const [contractRes, templateRes] = await Promise.all([
        getPurchaseContractOptions({
          product_id: detail.product_id,
          warehouse_id: detail.warehouse_id,
          qty: detail.qty_ton,
        }),
        getDeliveryTemplates(),
      ]);
      this.setData({
        purchaseContractOptions: contractRes.data || [],
        deliveryTemplates: templateRes.data || [],
      }, () => this.syncSelectionSummaries());
    } catch (error) {
      wx.showToast({ title: error.message || '加载提交选项失败', icon: 'none' });
    }
  },

  syncSelectionSummaries() {
    const selectedPurchaseContract = this.data.purchaseContractOptions[this.data.selectedPurchaseContractIndex] || null;
    const selectedDeliveryTemplate = this.data.deliveryTemplates[this.data.selectedDeliveryTemplateIndex] || null;
    this.setData({
      selectedPurchaseContract,
      selectedDeliveryTemplate,
    });
  },

  onPickPurchaseContract(e) {
    this.setData({ selectedPurchaseContractIndex: Number(e.detail.value || 0) }, () => this.syncSelectionSummaries());
  },

  onPickTemplate(e) {
    this.setData({ selectedDeliveryTemplateIndex: Number(e.detail.value || 0) }, () => this.syncSelectionSummaries());
  },

  onConfirmAckChange(e) {
    this.setData({ confirmAcknowledged: !!(e.detail.value || []).length });
  },

  onOutboundQtyInput(e) {
    this.setData({ outboundQty: String(e.detail.value || '').trim() });
  },

  onAdminReasonInput(e) {
    this.setData({ adminReason: String(e.detail.value || '').trim() });
  },

  async onUploadSupplierPayment() {
    try {
      this.skipNextOnShowReload = true;
      const uploaded = await chooseAndUploadFile('purchase-order-payment');
      const vouchers = this.data.supplierPaymentVouchers.concat([uploaded]);
      this.setData({ supplierPaymentVouchers: vouchers });
    } catch (error) {
      this.skipNextOnShowReload = false;
      wx.showToast({ title: error.message || '上传失败', icon: 'none' });
    }
  },

  onRemoveSupplierPaymentVoucher(e) {
    const index = Number(e.currentTarget.dataset.index);
    const vouchers = this.data.supplierPaymentVouchers.filter((_, i) => i !== index);
    this.setData({ supplierPaymentVouchers: vouchers });
  },

  async onUploadSupplierDoc() {
    try {
      this.skipNextOnShowReload = true;
      const uploaded = await chooseAndUploadFile('purchase-order-supplier-doc');
      this.setData({ supplierDeliveryDoc: uploaded });
    } catch (error) {
      this.skipNextOnShowReload = false;
      wx.showToast({ title: error.message || '上传失败', icon: 'none' });
    }
  },

  async onUploadOutboundDoc() {
    try {
      this.skipNextOnShowReload = true;
      const uploaded = await chooseAndUploadFile('purchase-order-outbound');
      this.setData({ outboundDoc: uploaded });
    } catch (error) {
      this.skipNextOnShowReload = false;
      wx.showToast({ title: error.message || '上传失败', icon: 'none' });
    }
  },

  async onSubmitPurchaseOrder() {
    const contract = this.data.purchaseContractOptions[this.data.selectedPurchaseContractIndex];
    const template = this.data.deliveryTemplates[this.data.selectedDeliveryTemplateIndex];
    if (!contract || !template) {
      wx.showToast({ title: '请选择采购合同和发货指令模板', icon: 'none' });
      return;
    }
    // BR-078：提交前必须上传至少一个付款凭证
    if (!this.data.supplierPaymentVouchers.length) {
      wx.showToast({ title: '请先上传向供应商的付款凭证', icon: 'none' });
      return;
    }
    if (!this.data.confirmAcknowledged) {
      wx.showToast({ title: '请先完成二次确认', icon: 'none' });
      return;
    }
    try {
      await submitPurchaseOrder(this.data.orderId, {
        purchase_contract_id: contract.purchase_contract_id,
        delivery_instruction_template_id: template.id,
        confirm_snapshot: {
          contract_no: contract.contract_no,
          supplier_company_name: contract.supplier_company_name,
          pending_execution_qty_ton: contract.pending_execution_qty_ton,
          projected_pending_execution_qty_ton: contract.projected_pending_execution_qty_ton,
          projected_over_execution_qty_ton: contract.projected_over_execution_qty_ton,
        },
        confirm_acknowledged: true,
        supplier_payment_voucher_file_keys: this.data.supplierPaymentVouchers.map((v) => v.file_key),
      });
      wx.showToast({ title: '采购订单已提交', icon: 'success' });
      this.loadData();
    } catch (error) {
      wx.showToast({ title: error.message || '提交失败', icon: 'none' });
    }
  },

  async onSupplierReview() {
    if (!this.data.supplierDeliveryDoc) {
      wx.showToast({ title: '请先上传盖章发货指令单', icon: 'none' });
      return;
    }
    try {
      await supplierReviewPurchaseOrder(this.data.orderId, this.data.supplierDeliveryDoc.file_key);
      wx.showToast({ title: '供应商确认完成', icon: 'success' });
      this.loadData();
    } catch (error) {
      wx.showToast({ title: error.message || '提交失败', icon: 'none' });
    }
  },

  async onWarehouseOutbound() {
    const qtyError = validateOutboundQty(this.data.outboundQty, this.data.detail && this.data.detail.qty_ton);
    if (qtyError) {
      wx.showToast({ title: qtyError, icon: 'none' });
      return;
    }
    if (!this.data.outboundDoc) {
      wx.showToast({ title: '请先上传出库单', icon: 'none' });
      return;
    }
    // 出库为不可撤销终态操作，需要二次确认
    const confirmed = await new Promise((resolve) => {
      wx.showModal({
        title: '确认出库',
        content: '出库后订单将进入完成状态，此操作不可撤销，请确认已核对单据信息。',
        confirmText: '确认出库',
        cancelText: '取消',
        success: (res) => resolve(res.confirm),
      });
    });
    if (!confirmed) return;
    try {
      await warehouseOutboundPurchaseOrder(this.data.orderId, {
        actual_outbound_qty: Number(this.data.outboundQty || 0),
        outbound_doc_file_key: this.data.outboundDoc.file_key,
      });
      wx.showToast({ title: '仓库出库完成', icon: 'success' });
      this.loadData();
    } catch (error) {
      wx.showToast({ title: error.message || '提交失败', icon: 'none' });
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
      await abnormalClosePurchaseOrder(this.data.orderId, this.data.adminReason);
      wx.showToast({ title: '采购订单已关闭', icon: 'success' });
      this.loadData();
    } catch (error) {
      wx.showToast({ title: error.message || '提交失败', icon: 'none' });
    }
  },

  async onOpenRemoteFile(e) {
    const url = e.currentTarget.dataset.url;
    const fileName = String(e.currentTarget.dataset.name || '').trim();
    if (!url) {
      wx.showToast({ title: '暂无附件', icon: 'none' });
      return;
    }
    try {
      await openRemoteFile(url, { fileName });
    } catch (error) {
      wx.showToast({ title: error.message || '打开失败', icon: 'none' });
    }
  },
});
