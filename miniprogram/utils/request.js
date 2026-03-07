const { getApiBaseUrl } = require('../config/env');
const { getAccessToken, logoutSession, saveAccessSession } = require('./session');

let refreshPromise = null;

function executeRawRequest({ url, method = 'GET', data = null, timeout = 12000, header = {}, skipAuth = false }) {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    return Promise.reject({
      message: '当前小程序仅开放演示模式，真实联调将在后续迭代接入',
      statusCode: 0,
    });
  }

  return new Promise((resolve, reject) => {
    const token = !skipAuth ? getAccessToken() : '';
    const requestHeaders = {
      'Content-Type': 'application/json',
      ...header,
    };
    if (token) {
      requestHeaders.Authorization = `Bearer ${token}`;
    }
    wx.request({
      url: `${baseUrl}${url}`,
      method,
      data,
      timeout,
      header: requestHeaders,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve({
            data: res.data,
            statusCode: res.statusCode,
          });
          return;
        }
        reject({
          message: (res.data && res.data.detail) || '请求失败',
          statusCode: res.statusCode,
        });
      },
      fail: (error) => {
        reject({
          message: error.errMsg || '网络请求失败',
          statusCode: 0,
        });
      },
    });
  });
}

function shouldTrySessionRefresh(error, options) {
  if (options.skipAuth || options._skipSessionRefresh || options._retry) {
    return false;
  }
  if (!getAccessToken()) {
    return false;
  }
  return Number(error && error.statusCode) === 401;
}

function normalizeRefreshProfile(payload) {
  return {
    user_id: payload.user_id,
    role_code: payload.role_code,
    company_id: payload.company_id,
    company_type: payload.company_type,
    client_type: payload.client_type,
    admin_web_allowed: Boolean(payload.admin_web_allowed),
    miniprogram_allowed: Boolean(payload.miniprogram_allowed),
  };
}

async function refreshAccessSession() {
  if (refreshPromise) {
    return refreshPromise;
  }
  refreshPromise = (async () => {
    const response = await executeRawRequest({
      url: '/access/session/refresh',
      method: 'POST',
      skipAuth: false,
      _skipSessionRefresh: true,
    });
    const payload = response && response.data ? response.data : {};
    const accessToken = String(payload.access_token || '').trim();
    if (!accessToken) {
      throw {
        message: '会话续期失败，请重新登录',
        statusCode: 401,
      };
    }
    saveAccessSession({
      accessToken,
      profile: normalizeRefreshProfile(payload),
    });
  })();
  try {
    await refreshPromise;
  } catch (error) {
    const statusCode = Number(error && error.statusCode);
    if (statusCode === 401 || statusCode === 403) {
      logoutSession();
    }
    throw error;
  } finally {
    refreshPromise = null;
  }
}

async function request(options) {
  const requestOptions = {
    method: 'GET',
    data: null,
    timeout: 12000,
    header: {},
    skipAuth: false,
    _skipSessionRefresh: false,
    _retry: false,
    ...options,
  };

  try {
    return await executeRawRequest(requestOptions);
  } catch (error) {
    if (!shouldTrySessionRefresh(error, requestOptions)) {
      throw error;
    }
    await refreshAccessSession();
    return executeRawRequest({
      ...requestOptions,
      _retry: true,
    });
  }
}

module.exports = {
  request,
};
