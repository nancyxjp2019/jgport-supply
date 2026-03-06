const STORAGE_RUNTIME_MODE_KEY = 'mini_runtime_mode';
const STORAGE_DEMO_ROLE_KEY = 'mini_demo_role_code';

const RUNTIME_MODES = Object.freeze({
  demo: {
    key: 'demo',
    label: '演示模式',
    apiBaseUrl: '',
  },
});

const DEMO_ACTORS = Object.freeze({
  operations: {
    userId: 'AUTO-TEST-MINI-OPS-001',
    roleCode: 'operations',
    roleLabel: '运营',
    companyId: 'AUTO-TEST-OPERATOR-COMPANY',
    companyType: 'operator_company',
    clientType: 'miniprogram',
  },
  finance: {
    userId: 'AUTO-TEST-MINI-FIN-001',
    roleCode: 'finance',
    roleLabel: '财务',
    companyId: 'AUTO-TEST-OPERATOR-COMPANY',
    companyType: 'operator_company',
    clientType: 'miniprogram',
  },
  admin: {
    userId: 'AUTO-TEST-MINI-ADMIN-001',
    roleCode: 'admin',
    roleLabel: '管理员',
    companyId: 'AUTO-TEST-OPERATOR-COMPANY',
    companyType: 'operator_company',
    clientType: 'miniprogram',
  },
  customer: {
    userId: 'AUTO-TEST-MINI-CUSTOMER-001',
    roleCode: 'customer',
    roleLabel: '客户',
    companyId: 'AUTO-TEST-CUSTOMER-COMPANY',
    companyType: 'customer_company',
    clientType: 'miniprogram',
  },
  supplier: {
    userId: 'AUTO-TEST-MINI-SUPPLIER-001',
    roleCode: 'supplier',
    roleLabel: '供应商',
    companyId: 'AUTO-TEST-SUPPLIER-COMPANY',
    companyType: 'supplier_company',
    clientType: 'miniprogram',
  },
  warehouse: {
    userId: 'AUTO-TEST-MINI-WAREHOUSE-001',
    roleCode: 'warehouse',
    roleLabel: '仓库',
    companyId: 'AUTO-TEST-WAREHOUSE-COMPANY',
    companyType: 'warehouse_company',
    clientType: 'miniprogram',
  },
});

function normalizeRuntimeMode(value) {
  return value === 'demo' ? value : 'demo';
}

function getRuntimeMode() {
  if (typeof wx === 'undefined' || typeof wx.getStorageSync !== 'function') {
    return 'demo';
  }
  return normalizeRuntimeMode(wx.getStorageSync(STORAGE_RUNTIME_MODE_KEY));
}

function getRuntimeModeLabel(mode) {
  const normalizedMode = normalizeRuntimeMode(mode);
  return (RUNTIME_MODES[normalizedMode] || RUNTIME_MODES.demo).label;
}

function getApiBaseUrl() {
  const mode = getRuntimeMode();
  return (RUNTIME_MODES[mode] || RUNTIME_MODES.demo).apiBaseUrl;
}

function normalizeDemoRoleCode(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return DEMO_ACTORS[normalized] ? normalized : 'operations';
}

function getDemoActor() {
  if (typeof wx === 'undefined' || typeof wx.getStorageSync !== 'function') {
    return DEMO_ACTORS.operations;
  }
  const roleCode = normalizeDemoRoleCode(wx.getStorageSync(STORAGE_DEMO_ROLE_KEY));
  return DEMO_ACTORS[roleCode];
}

module.exports = {
  DEMO_ACTORS,
  getApiBaseUrl,
  getDemoActor,
  getRuntimeMode,
  getRuntimeModeLabel,
};
