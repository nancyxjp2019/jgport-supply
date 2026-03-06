const { getApiBaseUrl } = require('../config/env');
const { getAccessToken } = require('./session');

function request({ url, method = 'GET', data = null, timeout = 12000, header = {}, skipAuth = false }) {
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

module.exports = {
  request,
};
