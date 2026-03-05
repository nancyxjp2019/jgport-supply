const { createSalesOrder, deleteTransportProfile, getSalesOrderCreateMeta, getTransportHistory } = require('../../../utils/api');
const { chooseAndUploadFile } = require('../../../utils/file');
const { formatNumber, todayText } = require('../../../utils/format');

const CHINA_MOBILE_PATTERN = /^1[3-9]\d{9}$/;
const VEHICLE_PLATE_PATTERN = /^[\u4e00-\u9fa5][A-Z](?:[A-HJ-NP-Z0-9]{5}|[DF][A-HJ-NP-Z0-9]{5}|[A-HJ-NP-Z0-9]{5}[DF])$/;

function containsWhitespace(value) {
  return /\s/.test(String(value || ''));
}

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

function normalizePlateNo(value) {
  return String(value || '').trim().toUpperCase();
}

function normalizeIdNo(value) {
  return String(value || '').trim().toUpperCase();
}

function validateChinaIdNo(idNo) {
  const normalized = normalizeIdNo(idNo);
  if (!/^\d{17}[0-9X]$/.test(normalized)) {
    return false;
  }
  const birthText = normalized.slice(6, 14);
  const year = Number(birthText.slice(0, 4));
  const month = Number(birthText.slice(4, 6));
  const day = Number(birthText.slice(6, 8));
  const birthDate = new Date(year, month - 1, day);
  if (
    Number.isNaN(birthDate.getTime()) ||
    birthDate.getFullYear() !== year ||
    birthDate.getMonth() !== month - 1 ||
    birthDate.getDate() !== day
  ) {
    return false;
  }
  const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
  const checkMap = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'];
  const total = normalized
    .slice(0, 17)
    .split('')
    .reduce((sum, char, index) => sum + Number(char) * weights[index], 0);
  return checkMap[total % 11] === normalized.slice(-1);
}

function getTransportValidationMessage(form) {
  if (containsWhitespace(form.carrier_company)) {
    return '运输单位不能包含空格';
  }
  if (containsWhitespace(form.driver_name)) {
    return '司机姓名不能包含空格';
  }
  if (!/^[\u4e00-\u9fff]{1,4}$/.test(String(form.driver_name || ''))) {
    return '司机姓名必须为1到4个汉字';
  }
  if (containsWhitespace(form.driver_phone)) {
    return '手机号不能包含空格';
  }
  if (!CHINA_MOBILE_PATTERN.test(String(form.driver_phone || ''))) {
    return '手机号格式不正确';
  }
  if (containsWhitespace(form.driver_id_no)) {
    return '身份证不能包含空格';
  }
  if (!validateChinaIdNo(form.driver_id_no)) {
    return '身份证格式不正确';
  }
  if (containsWhitespace(form.vehicle_no)) {
    return '车牌号不能包含空格';
  }
  if (!VEHICLE_PLATE_PATTERN.test(normalizePlateNo(form.vehicle_no))) {
    return '车牌号格式不正确';
  }
  if (form.tank_type && !['单枪', '双枪'].includes(normalizeTankType(form.tank_type))) {
    return '单双枪仅支持单枪或双枪';
  }
  if (form.rated_load_ton) {
    const ratedLoad = Number(form.rated_load_ton);
    if (!Number.isInteger(ratedLoad) || ratedLoad <= 0) {
      return '核定载重必须为正整数';
    }
  }
  return '';
}

function buildTransportHistory(items = []) {
  return items.map((item, index) => {
    const snapshot = item.transport_snapshot || {};
    return {
      ...item,
      display_text:
        [snapshot.vehicle_no, snapshot.driver_name].filter(Boolean).join(' / ') || `历史记录${index + 1}`,
      summary_text: [snapshot.carrier_company, snapshot.driver_phone, normalizeTankType(snapshot.tank_type)]
        .filter(Boolean)
        .join(' · '),
    };
  });
}

function buildContractTip(contract) {
  if (!contract) {
    return '当前无可选合同';
  }
  return `${contract.contract_no} / 待执行 ${formatNumber(contract.pending_execution_qty_ton, 4)} 吨`;
}

function filterProductOptionsByContract(productOptions = [], contract) {
  if (!contract) {
    return productOptions;
  }
  return productOptions.filter((item) => Number(item.id) === Number(contract.product_id));
}

function filterWarehouseOptionsByContract(warehouseOptions = [], warehouseProductStockPairs = [], contract) {
  if (!contract) {
    return warehouseOptions;
  }
  return warehouseOptions.filter((item) =>
    warehouseProductStockPairs.some(
      (pair) => Number(pair.warehouse_id) === Number(item.id) && Number(pair.product_id) === Number(contract.product_id),
    ),
  );
}

function buildWarehouseTip(contract, warehouseOptions = []) {
  if (!contract) {
    return '请先选择合同';
  }
  if (!warehouseOptions.length) {
    return '当前合同油品暂无可用仓库';
  }
  return '仓库按当前合同油品库存自动过滤';
}

function findIndexById(options = [], targetId) {
  const index = options.findIndex((item) => Number(item.id) === Number(targetId));
  return index >= 0 ? index : 0;
}

Page({
  data: {
    loading: false,
    warehouseOptions: [],
    sourceWarehouseOptions: [],
    warehouseProductStockPairs: [],
    productOptions: [],
    sourceProductOptions: [],
    salesContracts: [],
    transportHistory: [],
    selectedContractTip: '当前无可选合同',
    selectedWarehouseTip: '请先选择合同',
    selectedWarehouseIndex: 0,
    selectedProductIndex: 0,
    selectedContractIndex: 0,
    tankTypeOptions: ['单枪', '双枪'],
    attachments: [],
    form: {
      order_date: todayText(),
      qty_ton: '',
      carrier_company: '',
      driver_name: '',
      driver_phone: '',
      driver_id_no: '',
      vehicle_no: '',
      tank_type: '',
      rated_load_ton: '',
      with_pump: false,
      remark: '',
      transport_profile_id: '',
    },
  },

  onShow() {
    if (this.skipNextOnShowReload) {
      this.skipNextOnShowReload = false;
      return;
    }
    this.loadMeta();
  },

  async loadMeta() {
    this.setData({ loading: true });
    try {
      const [metaRes, historyRes] = await Promise.all([getSalesOrderCreateMeta(), getTransportHistory()]);
      const data = metaRes.data || {};
      const sourceWarehouseOptions = data.warehouses || [];
      const warehouseProductStockPairs = data.warehouse_product_stock_pairs || [];
      const sourceProductOptions = data.products || [];
      const salesContracts = data.sales_contracts || [];
      const initialContract = salesContracts[0] || null;
      const warehouseOptions = filterWarehouseOptionsByContract(sourceWarehouseOptions, warehouseProductStockPairs, initialContract);
      const productOptions = filterProductOptionsByContract(sourceProductOptions, initialContract);
      this.setData({
        warehouseOptions,
        sourceWarehouseOptions,
        warehouseProductStockPairs,
        productOptions,
        sourceProductOptions,
        salesContracts,
        transportHistory: buildTransportHistory(historyRes.data || []),
        selectedContractTip: buildContractTip(initialContract),
        selectedWarehouseTip: buildWarehouseTip(initialContract, warehouseOptions),
        selectedProductIndex: findIndexById(productOptions, initialContract && initialContract.product_id),
        selectedContractIndex: 0,
        selectedWarehouseIndex: 0,
      });
    } catch (error) {
      wx.showToast({ title: error.message || '加载基础数据失败', icon: 'none' });
    }
    this.setData({ loading: false });
  },

  async loadTransportHistory() {
    const historyRes = await getTransportHistory();
    this.setData({ transportHistory: buildTransportHistory(historyRes.data || []) });
  },

  syncContractDrivenOptions(contractIndex) {
    const contract = this.data.salesContracts[contractIndex] || null;
    const warehouseOptions = filterWarehouseOptionsByContract(
      this.data.sourceWarehouseOptions,
      this.data.warehouseProductStockPairs,
      contract,
    );
    const productOptions = filterProductOptionsByContract(this.data.sourceProductOptions, contract);
    this.setData({
      warehouseOptions,
      productOptions,
      selectedContractIndex: contract ? contractIndex : 0,
      selectedProductIndex: findIndexById(productOptions, contract && contract.product_id),
      selectedWarehouseIndex: 0,
      selectedContractTip: buildContractTip(contract),
      selectedWarehouseTip: buildWarehouseTip(contract, warehouseOptions),
    });
  },

  onOrderDateChange(e) {
    this.setData({ 'form.order_date': e.detail.value });
  },

  onQtyInput(e) {
    this.setData({ 'form.qty_ton': String(e.detail.value || '').trim() });
  },

  onWarehouseChange(e) {
    this.setData({ selectedWarehouseIndex: Number(e.detail.value || 0) });
  },

  onProductChange(e) {
    const selectedProductIndex = Number(e.detail.value || 0);
    this.setData({ selectedProductIndex });
  },

  onContractChange(e) {
    const selectedContractIndex = Number(e.detail.value || 0);
    this.syncContractDrivenOptions(selectedContractIndex);
  },

  onFieldInput(e) {
    const field = e.currentTarget.dataset.field;
    if (!field) {
      return;
    }
    let value = String(e.detail.value || '').trim();
    if (field === 'vehicle_no') {
      value = normalizePlateNo(value);
    }
    if (field === 'driver_id_no') {
      value = normalizeIdNo(value);
    }
    this.setData({ [`form.${field}`]: value });
  },

  onTankTypeSelect(e) {
    this.setData({ 'form.tank_type': normalizeTankType(e.currentTarget.dataset.value) });
  },

  onPumpOptionSelect(e) {
    this.setData({ 'form.with_pump': String(e.currentTarget.dataset.value || '') === '1' });
  },

  onUseHistory(e) {
    const index = Number(e.currentTarget.dataset.index);
    const profile = this.data.transportHistory[index];
    if (!profile || !profile.transport_snapshot) {
      return;
    }
    const snapshot = profile.transport_snapshot;
    this.setData({
      'form.transport_profile_id': profile.id,
      'form.carrier_company': snapshot.carrier_company || '',
      'form.driver_name': snapshot.driver_name || '',
      'form.driver_phone': snapshot.driver_phone || '',
      'form.driver_id_no': normalizeIdNo(snapshot.driver_id_no || ''),
      'form.vehicle_no': normalizePlateNo(snapshot.vehicle_no || ''),
      'form.tank_type': normalizeTankType(snapshot.tank_type || ''),
      'form.rated_load_ton': snapshot.rated_load_ton ? `${snapshot.rated_load_ton}` : '',
      'form.with_pump': !!snapshot.with_pump,
      'form.remark': snapshot.remark || '',
    });
  },

  async onDeleteHistory(e) {
    const index = Number(e.currentTarget.dataset.index);
    const profile = this.data.transportHistory[index];
    if (!profile) {
      return;
    }
    const confirmRes = await new Promise((resolve) => {
      wx.showModal({
        title: '删除历史运输信息',
        content: `确认删除“${profile.display_text}”吗？删除后仅不再用于预选，不影响历史订单。`,
        confirmText: '删除',
        confirmColor: '#af3b2f',
        success: resolve,
        fail: () => resolve({ confirm: false }),
      });
    });
    if (!confirmRes.confirm) {
      return;
    }

    this.setData({ loading: true });
    try {
      await deleteTransportProfile(profile.id);
      if (Number(this.data.form.transport_profile_id) === Number(profile.id)) {
        this.setData({ 'form.transport_profile_id': '' });
      }
      await this.loadTransportHistory();
      wx.showToast({ title: '历史运输信息已删除', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: error.message || '删除失败', icon: 'none' });
    }
    this.setData({ loading: false });
  },

  async onAddAttachment() {
    try {
      this.skipNextOnShowReload = true;
      const uploaded = await chooseAndUploadFile('sales-order-payment');
      const attachments = this.data.attachments.concat({
        file_key: uploaded.file_key,
        file_name: uploaded.original_filename || uploaded.file_key,
      });
      this.setData({ attachments });
    } catch (error) {
      this.skipNextOnShowReload = false;
      wx.showToast({ title: error.message || '上传失败', icon: 'none' });
    }
  },

  onRemoveAttachment(e) {
    const index = Number(e.currentTarget.dataset.index);
    const attachments = this.data.attachments.slice();
    attachments.splice(index, 1);
    this.setData({ attachments });
  },

  async onSubmit() {
    const warehouse = this.data.warehouseOptions[this.data.selectedWarehouseIndex];
    const product = this.data.productOptions[this.data.selectedProductIndex];
    const contract = this.data.salesContracts[this.data.selectedContractIndex];
    const qty = Number(this.data.form.qty_ton);
    if (!contract || !product) {
      wx.showToast({ title: '请完整选择合同、油品和仓库', icon: 'none' });
      return;
    }
    if (!warehouse) {
      wx.showToast({ title: '当前合同油品暂无可用仓库', icon: 'none' });
      return;
    }
    if (!Number.isFinite(qty) || qty <= 0) {
      wx.showToast({ title: '请输入正确的数量', icon: 'none' });
      return;
    }
    const requiredFields = ['carrier_company', 'driver_name', 'driver_phone', 'driver_id_no', 'vehicle_no'];
    const missingField = requiredFields.find((item) => !this.data.form[item]);
    if (missingField) {
      wx.showToast({ title: '请补全运输信息必填项', icon: 'none' });
      return;
    }
    if (!this.data.attachments.length) {
      wx.showToast({ title: '请先上传付款凭证', icon: 'none' });
      return;
    }
    const transportValidationMessage = getTransportValidationMessage(this.data.form);
    if (transportValidationMessage) {
      wx.showToast({ title: transportValidationMessage, icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    try {
      const res = await createSalesOrder({
        order_date: this.data.form.order_date,
        warehouse_id: warehouse.id,
        product_id: product.id,
        sales_contract_id: contract.sales_contract_id,
        qty_ton: qty,
        transport_profile_id: this.data.form.transport_profile_id ? Number(this.data.form.transport_profile_id) : null,
        transport_snapshot: {
          carrier_company: this.data.form.carrier_company,
          driver_name: this.data.form.driver_name,
          driver_phone: this.data.form.driver_phone,
          driver_id_no: normalizeIdNo(this.data.form.driver_id_no),
          vehicle_no: normalizePlateNo(this.data.form.vehicle_no),
          tank_type: normalizeTankType(this.data.form.tank_type) || null,
          with_pump: !!this.data.form.with_pump,
          rated_load_ton: this.data.form.rated_load_ton ? Number(this.data.form.rated_load_ton) : null,
          remark: this.data.form.remark || null,
        },
        transport_file_keys: this.data.attachments.map((item) => item.file_key),
      });
      wx.showToast({ title: '建单成功', icon: 'success' });
      wx.redirectTo({ url: `/pages/sales-orders/detail/index?id=${res.data.id}` });
    } catch (error) {
      wx.showToast({ title: error.message || '建单失败', icon: 'none' });
    }
    this.setData({ loading: false });
  },
});
