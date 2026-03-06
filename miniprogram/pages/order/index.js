const { getRuntimeMode, getRuntimeModeLabel } = require('../../config/env');
const {
  createSalesOrderDraft,
  getAccessProfile,
  getAvailableSalesContracts,
  listSalesOrders,
  submitSalesOrder,
  updateSalesOrderDraft,
} = require('../../utils/api');
const { formatDateTime, formatMoney, formatQty } = require('../../utils/format');
const { getRoleLabel } = require('../../utils/light-report');
const { resolveHomePath } = require('../../utils/navigation');
const { getAccessToken, initializeSession, logoutSession, updateAccessProfile } = require('../../utils/session');
const {
  adaptContractOptions,
  buildOrderDraftPayload,
  buildOrderEditorState,
  canEditOrder,
  getOrderStatusClass,
  getOrderStatusOptions,
  validateSubmitComment,
} = require('../../utils/order');

function buildInitialForm() {
  return {
    salesContractId: '',
    oilProductId: '',
    qty: '',
    unitPrice: '',
    submitComment: '',
  };
}

function resolveContractSelection(contractOptions, selectedContractIndex) {
  const safeIndex = contractOptions.length ? Math.max(0, Math.min(selectedContractIndex, contractOptions.length - 1)) : 0;
  const contract = contractOptions[safeIndex] || null;
  const oilOptions = contract ? contract.items : [];
  const oil = oilOptions[0] || null;
  return {
    selectedContractIndex: safeIndex,
    oilOptions,
    selectedOilIndex: 0,
    salesContractId: contract ? String(contract.id) : '',
    oilProductId: oil ? oil.oilProductId : '',
    unitPrice: oil ? String(oil.unitPrice) : '',
  };
}

Page({
  data: {
    loading: true,
    querying: false,
    savingDraft: false,
    submitting: false,
    allowed: false,
    errorMessage: '',
    listErrorMessage: '',
    roleLabel: '',
    runtimeLabel: '演示模式',
    activeTab: 'create',
    statusOptions: getOrderStatusOptions(),
    statusFilter: '',
    contractOptions: [],
    oilOptions: [],
    selectedContractIndex: 0,
    selectedOilIndex: 0,
    form: buildInitialForm(),
    fieldErrors: {},
    orders: [],
    emptyText: '暂无订单数据',
    editingOrderId: null,
    editingOrderNo: '',
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
          loading: false,
          allowed: false,
          errorMessage: error.message || '读取登录身份失败，请确认本地后端已启动',
          roleLabel: currentUser ? currentUser.roleLabel : '',
          runtimeLabel: getRuntimeModeLabel(runtimeMode),
        });
        return;
      }
    }
    if (!currentUser) {
      this._redirectToLogin();
      return;
    }

    const roleLabel = getRoleLabel(currentUser.roleCode);
    const allowed = currentUser.roleCode === 'customer';
    this.setData({
      loading: true,
      allowed,
      errorMessage: '',
      roleLabel,
      runtimeLabel: getRuntimeModeLabel(runtimeMode),
    });

    if (!allowed) {
      this.setData({
        loading: false,
      });
      return;
    }

    try {
      const [contractsResponse, ordersResponse] = await Promise.all([
        getAvailableSalesContracts(),
        listSalesOrders(this.data.statusFilter),
      ]);
      const contractOptions = adaptContractOptions(contractsResponse.data.items);
      const selection = resolveContractSelection(contractOptions, 0);
      this.setData({
        loading: false,
        contractOptions,
        oilOptions: selection.oilOptions,
        selectedContractIndex: selection.selectedContractIndex,
        selectedOilIndex: selection.selectedOilIndex,
        form: {
          ...buildInitialForm(),
          salesContractId: selection.salesContractId,
          oilProductId: selection.oilProductId,
          unitPrice: selection.unitPrice,
        },
        orders: this._decorateOrders(ordersResponse.data.items),
        emptyText: contractsResponse.data.total ? '暂无订单数据' : '当前没有可用合同，请联系运营或财务确认合同状态',
      });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '订单页面加载失败，请稍后重试',
      });
    }
  },

  onSwitchTab(event) {
    this.setData({
      activeTab: String(event.currentTarget.dataset.tab || 'create'),
      errorMessage: '',
      listErrorMessage: '',
    });
  },

  onSelectContract(event) {
    const selectedContractIndex = Number(event.detail.value || 0);
    const selection = resolveContractSelection(this.data.contractOptions, selectedContractIndex);
    this.setData({
      selectedContractIndex: selection.selectedContractIndex,
      selectedOilIndex: selection.selectedOilIndex,
      oilOptions: selection.oilOptions,
      'form.salesContractId': selection.salesContractId,
      'form.oilProductId': selection.oilProductId,
      'form.unitPrice': selection.unitPrice,
      'fieldErrors.salesContractId': '',
      'fieldErrors.oilProductId': '',
      'fieldErrors.unitPrice': '',
    });
  },

  onSelectOil(event) {
    const selectedOilIndex = Number(event.detail.value || 0);
    const oilOption = this.data.oilOptions[selectedOilIndex] || null;
    this.setData({
      selectedOilIndex,
      'form.oilProductId': oilOption ? oilOption.oilProductId : '',
      'form.unitPrice': oilOption ? String(oilOption.unitPrice) : '',
      'fieldErrors.oilProductId': '',
      'fieldErrors.unitPrice': '',
    });
  },

  onFieldInput(event) {
    const field = String(event.currentTarget.dataset.field || '').trim();
    if (!field) {
      return;
    }
    this.setData({
      [`form.${field}`]: event.detail.value,
      [`fieldErrors.${field}`]: '',
    });
  },

  async onSaveDraft() {
    await this._saveOrder(false);
  },

  async onSubmitApproval() {
    await this._saveOrder(true);
  },

  async _saveOrder(shouldSubmit) {
    if (!this.data.allowed || this.data.savingDraft || this.data.submitting) {
      return;
    }
    const validation = buildOrderDraftPayload(this.data.form);
    if (shouldSubmit) {
      validation.errors.submitComment = validateSubmitComment(this.data.form.submitComment);
      validation.isValid = validation.isValid && !validation.errors.submitComment;
    }
    if (!validation.isValid) {
      this.setData({ fieldErrors: validation.errors });
      wx.showToast({ title: '请先完成表单信息', icon: 'none' });
      return;
    }

    this.setData({
      savingDraft: !shouldSubmit,
      submitting: shouldSubmit,
      errorMessage: '',
      fieldErrors: {},
    });
    try {
      const draftResponse = this.data.editingOrderId
        ? await updateSalesOrderDraft(this.data.editingOrderId, validation.payload)
        : await createSalesOrderDraft(validation.payload);
      if (shouldSubmit) {
        await submitSalesOrder(draftResponse.data.id, this.data.form.submitComment);
      }
      wx.showToast({
        title: shouldSubmit ? '订单已提交审批' : '草稿已保存',
        icon: 'success',
      });
      await this._reloadOrders();
      this._resetEditor();
      this.setData({
        activeTab: 'query',
        errorMessage: '',
        listErrorMessage: '',
      });
    } catch (error) {
      this.setData({
        errorMessage: error.message || '订单保存失败，请稍后重试',
      });
      wx.showToast({ title: error.message || '操作失败', icon: 'none' });
    } finally {
      this.setData({
        savingDraft: false,
        submitting: false,
      });
    }
  },

  async onRefreshOrders() {
    await this._reloadOrders();
  },

  async onFilterStatus(event) {
    this.setData({
      statusFilter: String(event.currentTarget.dataset.status || ''),
    });
    await this._reloadOrders();
  },

  onEditOrder(event) {
    const orderId = Number(event.currentTarget.dataset.orderId || 0);
    const order = this.data.orders.find((item) => item.id === orderId);
    if (!order || !canEditOrder(order.status)) {
      return;
    }
    const editorState = buildOrderEditorState(order, this.data.contractOptions);
    const selectedContract = this.data.contractOptions[editorState.selectedContractIndex] || null;
    this.setData({
      activeTab: 'create',
      editingOrderId: editorState.editingOrderId,
      editingOrderNo: order.order_no,
      selectedContractIndex: editorState.selectedContractIndex,
      selectedOilIndex: editorState.selectedOilIndex,
      oilOptions: selectedContract ? selectedContract.items : [],
      form: editorState.form,
      errorMessage: '',
      fieldErrors: {},
    });
  },

  onResetForm() {
    this._resetEditor();
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

  async _reloadOrders() {
    this.setData({
      querying: true,
      listErrorMessage: '',
    });
    try {
      const response = await listSalesOrders(this.data.statusFilter);
      this.setData({
        orders: this._decorateOrders(response.data.items),
      });
    } catch (error) {
      this.setData({
        listErrorMessage: error.message || '订单列表加载失败，请稍后重试',
      });
    } finally {
      this.setData({
        querying: false,
      });
    }
  },

  _decorateOrders(items) {
    return (items || []).map((item) => ({
      ...item,
      statusClass: getOrderStatusClass(item.status),
      qtyOrderedText: formatQty(item.qty_ordered),
      unitPriceText: formatMoney(item.unit_price),
      createdAtText: formatDateTime(item.created_at),
      submittedAtText: formatDateTime(item.submitted_at),
      canEdit: canEditOrder(item.status),
    }));
  },

  _resetEditor() {
    const selection = resolveContractSelection(this.data.contractOptions, 0);
    this.setData({
      editingOrderId: null,
      editingOrderNo: '',
      selectedContractIndex: selection.selectedContractIndex,
      selectedOilIndex: selection.selectedOilIndex,
      oilOptions: selection.oilOptions,
      form: {
        ...buildInitialForm(),
        salesContractId: selection.salesContractId,
        oilProductId: selection.oilProductId,
        unitPrice: selection.unitPrice,
      },
      fieldErrors: {},
      errorMessage: '',
    });
  },

  _redirectToLogin() {
    this.setData({
      loading: false,
      allowed: false,
      errorMessage: '',
      roleLabel: '',
      runtimeLabel: getRuntimeModeLabel(getRuntimeMode()),
    });
    wx.reLaunch({ url: '/pages/login/index' });
  },
});
