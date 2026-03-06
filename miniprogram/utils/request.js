const { getApiBaseUrl } = require('../config/env');

function request({ url, method = 'GET', data = null, timeout = 12000 }) {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    return Promise.reject({
      message: '当前小程序仅开放演示模式，真实联调将在后续迭代接入',
      statusCode: 0,
    });
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${baseUrl}${url}`,
      method,
      data,
      timeout,
      header: {
        'Content-Type': 'application/json',
      },
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
