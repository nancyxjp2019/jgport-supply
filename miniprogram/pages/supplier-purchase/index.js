const { getRuntimeMode, getRuntimeModeLabel } = require('../../config/env');
const {
  confirmSupplierPurchaseOrderDelivery,
  createSupplierPurchaseOrderAttachment,
  getAccessProfile,
  getSupplierPurchaseOrderDetail,
  listSupplierPurchaseOrderAttachments,
  listSupplierPurchaseOrders,
} = require('../../utils/api');
const { formatDateTime, formatMoney, formatQty } = require('../../utils/format');
const { getRoleLabel } = require('../../utils/light-report');
const { resolveEntrySourceMeta, resolveHomePath } = require('../../utils/navigation');
const { getAccessToken, initializeSession, logoutSession, updateAccessProfile } = require('../../utils/session');
const {
  buildSupplierPreparationHints,
  buildSupplierAttachmentItems,
  buildSupplierSummaryCards,
  getSupplierAttachmentTagOptions,
  resolvePurchaseOrderStatusClass,
  resolveSupplierAttachmentTagLabel,
} = require('../../utils/supplier-purchase');

function buildInitialState() {
  return {
    loading: true,
    detailLoading: false,
    allowed: false,
    errorMessage: '',
    detailErrorMessage: '',
    roleLabel: '',
    runtimeLabel: '演示模式',
    sourceText: '',
    sourceDetailText: '',
    summaryCards: [],
    orders: [],
    selectedOrderId: 0,
    selectedOrder: null,
    attachments: [],
    attachmentLoading: false,
    attachmentErrorMessage: '',
    attachmentSubmitting: false,
    attachmentBizTagOptions: getSupplierAttachmentTagOptions(),
    attachmentBizTagIndex: 0,
    attachmentFilePath: '',
    deliveryConfirmComment: '',
    deliveryConfirmSubmitting: false,
    deliveryConfirmErrorMessage: '',
    emptyText: '当前暂无可查看的采购订单。',
  };
}

Page({
  data: buildInitialState(),

  onLoad(options) {
    const sourceMeta = resolveEntrySourceMeta(options);
    const selectedOrderId = Number((options && options.orderId) || 0);
    this.setData({
      selectedOrderId,
      sourceText: sourceMeta.sourceText,
      sourceDetailText: sourceMeta.sourceDetailText,
    });
  },

  onShow() {
    this.loadPage();
  },

  async loadPage() {
    const runtimeMode = getRuntimeMode();
    let currentUser = initializeSession();
    if (['local_api', 'wechat_auth'].includes(runtimeMode)) {
      if (!getAccessToken() || !currentUser) {
        this._redirectToLogin();
        return;
      }
      try {
        const response = await getAccessProfile();
        currentUser = updateAccessProfile(response.data);
      } catch (error) {
        if (Number(error.statusCode || 0) === 401) {
          logoutSession();
          wx.showToast({ title: error.message || '登录状态已失效，请重新登录', icon: 'none' });
          this._redirectToLogin();
          return;
        }
        this.setData({
          ...buildInitialState(),
          loading: false,
          errorMessage: error.message || '读取登录身份失败，请确认本地后端已启动',
          roleLabel: currentUser ? currentUser.roleLabel : '',
          runtimeLabel: getRuntimeModeLabel(runtimeMode),
          sourceText: this.data.sourceText,
          sourceDetailText: this.data.sourceDetailText,
          selectedOrderId: this.data.selectedOrderId,
        });
        return;
      }
    }
    if (!currentUser) {
      this._redirectToLogin();
      return;
    }

    const allowed = currentUser.roleCode === 'supplier';
    this.setData({
      ...buildInitialState(),
      loading: true,
      allowed,
      roleLabel: getRoleLabel(currentUser.roleCode),
      runtimeLabel: getRuntimeModeLabel(runtimeMode),
      sourceText: this.data.sourceText,
      sourceDetailText: this.data.sourceDetailText,
      selectedOrderId: this.data.selectedOrderId,
    });

    if (!allowed) {
      this.setData({ loading: false });
      return;
    }

    try {
      const response = await listSupplierPurchaseOrders('', { limit: 20 });
      const orders = this._decorateOrders(response.data.items || []);
      const selectedOrderId = this._resolveSelectedOrderId(orders, this.data.selectedOrderId);
      this.setData({
        loading: false,
        summaryCards: buildSupplierSummaryCards(response.data.items || []),
        orders,
        selectedOrderId,
        emptyText: response.data.total ? '请选择一条采购订单查看详情。' : '当前暂无可查看的采购订单。',
      });
      if (selectedOrderId > 0) {
        await this._loadDetail(selectedOrderId);
      }
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '供应商采购进度加载失败，请稍后重试',
      });
    }
  },

  onOpenOrder(event) {
    const orderId = Number(event.currentTarget.dataset.orderId || 0);
    if (!orderId || orderId === this.data.selectedOrderId) {
      return;
    }
    this.setData({ selectedOrderId: orderId });
    this._loadDetail(orderId);
  },

  onOpenDefaultPage() {
    const currentUser = initializeSession();
    wx.reLaunch({ url: resolveHomePath(currentUser ? currentUser.roleCode : '') });
  },

  onSwitchRole() {
    wx.reLaunch({ url: '/pages/login/index' });
  },

  onLogout() {
    logoutSession();
    wx.reLaunch({ url: '/pages/login/index' });
  },

  onAttachmentTagChange(event) {
    this.setData({ attachmentBizTagIndex: Number(event.detail.value || 0) });
  },

  onAttachmentFilePathInput(event) {
    this.setData({ attachmentFilePath: String(event.detail.value || '').trim() });
  },

  onDeliveryConfirmCommentInput(event) {
    this.setData({
      deliveryConfirmComment: String(event.detail.value || '').trim(),
    });
  },

  onFillDemoAttachmentPath() {
    const selectedOrder = this.data.selectedOrder;
    const tag = this.data.attachmentBizTagOptions[this.data.attachmentBizTagIndex] || this.data.attachmentBizTagOptions[0];
    const orderNo = selectedOrder ? selectedOrder.order_no : 'PO-DEMO';
    const suffix = tag && tag.value === 'SUPPLIER_DELIVERY_RECEIPT' ? 'delivery-receipt' : 'stamped-doc';
    this.setData({
      attachmentFilePath: `CODEX-TEST-/${orderNo.toLowerCase()}-${suffix}.pdf`,
    });
  },

  async onSubmitAttachment() {
    const selectedOrder = this.data.selectedOrder;
    if (!selectedOrder || !selectedOrder.id) {
      wx.showToast({ title: '请先选择采购订单', icon: 'none' });
      return;
    }
    const option = this.data.attachmentBizTagOptions[this.data.attachmentBizTagIndex] || this.data.attachmentBizTagOptions[0];
    const filePath = String(this.data.attachmentFilePath || '').trim();
    if (!option || !option.value) {
      wx.showToast({ title: '请选择附件类型', icon: 'none' });
      return;
    }
    if (!filePath) {
      wx.showToast({ title: '请填写附件路径', icon: 'none' });
      return;
    }
    this.setData({ attachmentSubmitting: true, attachmentErrorMessage: '' });
    try {
      const response = await createSupplierPurchaseOrderAttachment(selectedOrder.id, {
        biz_tag: option.value,
        file_path: filePath,
      });
      wx.showToast({ title: response.data.message || '附件上传成功', icon: 'success' });
      this.setData({ attachmentFilePath: '' });
      await this._loadAttachments(selectedOrder.id);
    } catch (error) {
      this.setData({ attachmentErrorMessage: error.message || '附件上传失败，请稍后重试' });
    } finally {
      this.setData({ attachmentSubmitting: false });
    }
  },

  async onConfirmDelivery() {
    const selectedOrder = this.data.selectedOrder;
    const comment = String(this.data.deliveryConfirmComment || '').trim();
    if (!selectedOrder || !selectedOrder.id) {
      wx.showToast({ title: '请先选择采购订单', icon: 'none' });
      return;
    }
    if (!selectedOrder.canConfirmDelivery) {
      wx.showToast({ title: '当前状态不可重复确认', icon: 'none' });
      return;
    }
    if (!comment) {
      wx.showToast({ title: '请填写发货确认说明', icon: 'none' });
      return;
    }
    this.setData({
      deliveryConfirmSubmitting: true,
      deliveryConfirmErrorMessage: '',
    });
    try {
      const response = await confirmSupplierPurchaseOrderDelivery(
        selectedOrder.id,
        comment,
      );
      wx.showToast({
        title: response.data.message || '发货确认已提交',
        icon: 'success',
      });
      this.setData({ deliveryConfirmComment: '' });
      await this.loadPage();
    } catch (error) {
      this.setData({
        deliveryConfirmErrorMessage:
          error.message || '发货确认提交失败，请稍后重试',
      });
    } finally {
      this.setData({ deliveryConfirmSubmitting: false });
    }
  },

  async _loadDetail(orderId) {
    this.setData({
      detailLoading: true,
      detailErrorMessage: '',
      attachmentErrorMessage: '',
      deliveryConfirmErrorMessage: '',
      deliveryConfirmComment: '',
      attachmentLoading: false,
      attachments: [],
    });
    try {
      const response = await getSupplierPurchaseOrderDetail(orderId);
      const selectedOrder = this._decorateDetail(response.data, this.data.attachments);
      this.setData({
        detailLoading: false,
        selectedOrder,
      });
      await this._loadAttachments(orderId);
    } catch (error) {
      this.setData({
        detailLoading: false,
        selectedOrder: null,
        attachments: [],
        detailErrorMessage: error.message || '采购订单详情加载失败，请稍后重试',
      });
    }
  },

  async _loadAttachments(orderId) {
    this.setData({ attachmentLoading: true, attachmentErrorMessage: '' });
    try {
      const response = await listSupplierPurchaseOrderAttachments(orderId);
      const attachments = buildSupplierAttachmentItems(response.data.items || []).map((item) => ({
        ...item,
        createdAtText: formatDateTime(item.created_at),
      }));
      this.setData({
        attachmentLoading: false,
        attachments,
        selectedOrder: this._decorateDetail(this.data.selectedOrder, attachments),
      });
    } catch (error) {
      this.setData({
        attachmentLoading: false,
        attachments: [],
        attachmentErrorMessage: error.message || '附件摘要加载失败，请稍后重试',
        selectedOrder: this._decorateDetail(this.data.selectedOrder, []),
      });
    }
  },

  _resolveSelectedOrderId(orders, selectedOrderId) {
    const matched = (orders || []).find((item) => item.id === Number(selectedOrderId));
    if (matched) {
      return matched.id;
    }
    return orders.length ? orders[0].id : 0;
  },

  _decorateOrders(items) {
    return (items || []).map((item) => ({
      ...item,
      statusClass: resolvePurchaseOrderStatusClass(item.status),
      qtyOrderedText: formatQty(item.qty_ordered),
      payableAmountText: formatMoney(item.payable_amount),
      createdAtText: formatDateTime(item.created_at),
      selected: Number(item.id) === Number(this.data.selectedOrderId),
    }));
  },

  _decorateDetail(item, attachments) {
    if (!item) {
      return null;
    }
    const resolvedAttachments = Array.isArray(attachments) ? attachments : (Array.isArray(item.attachments) ? item.attachments : []);
    return {
      ...item,
      attachments: resolvedAttachments,
      statusClass: resolvePurchaseOrderStatusClass(item.status),
      qtyOrderedText: formatQty(item.qty_ordered),
      payableAmountText: formatMoney(item.payable_amount),
      createdAtText: formatDateTime(item.created_at),
      supplierConfirmedAtText: item.supplier_confirmed_at
        ? formatDateTime(item.supplier_confirmed_at)
        : '',
      canConfirmDelivery: item.status === '待供应商确认',
      primaryAttachmentTagLabel: resolveSupplierAttachmentTagLabel(
        resolvedAttachments.length ? resolvedAttachments[0].biz_tag : '',
      ),
      preparationHints: buildSupplierPreparationHints({
        ...item,
        attachments: resolvedAttachments,
      }),
    };
  },

  _redirectToLogin() {
    this.setData({
      ...buildInitialState(),
      loading: false,
      runtimeLabel: getRuntimeModeLabel(getRuntimeMode()),
    });
    wx.reLaunch({ url: '/pages/login/index' });
  },
});
