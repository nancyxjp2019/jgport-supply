const STORAGE_KEY = 'api_environment';

const ENVIRONMENTS = Object.freeze({
  local: {
    key: 'local',
    label: '本地环境',
    apiBaseUrl: 'http://127.0.0.1:8000/api/v1',
  },
  production: {
    key: 'production',
    label: '生产环境',
    apiBaseUrl: 'https://sd.jgport.top/api/v1',
  },
});

const DEFAULT_ENV_MAP = Object.freeze({
  develop: 'local',
  trial: 'production',
  release: 'production',
});

function normalizeEnvironmentKey(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'prod') {
    return 'production';
  }
  if (normalized === 'local' || normalized === 'production') {
    return normalized;
  }
  return '';
}

function getMiniProgramEnvVersion() {
  if (typeof wx === 'undefined' || typeof wx.getAccountInfoSync !== 'function') {
    return '';
  }
  try {
    const accountInfo = wx.getAccountInfoSync();
    return (accountInfo && accountInfo.miniProgram && accountInfo.miniProgram.envVersion) || '';
  } catch (_error) {
    return '';
  }
}

function getStoredEnvironmentKey() {
  if (typeof wx === 'undefined' || typeof wx.getStorageSync !== 'function') {
    return '';
  }
  return normalizeEnvironmentKey(wx.getStorageSync(STORAGE_KEY));
}

function getDefaultEnvironmentKey() {
  const envVersion = getMiniProgramEnvVersion();
  return DEFAULT_ENV_MAP[envVersion] || 'production';
}

function getCurrentEnvironmentKey() {
  return getStoredEnvironmentKey() || getDefaultEnvironmentKey();
}

function getCurrentEnvironment() {
  const key = getCurrentEnvironmentKey();
  return ENVIRONMENTS[key] || ENVIRONMENTS.production;
}

function getApiBaseUrl() {
  return getCurrentEnvironment().apiBaseUrl;
}

module.exports = {
  ENVIRONMENTS,
  getApiBaseUrl,
  getCurrentEnvironment,
  getCurrentEnvironmentKey,
};
