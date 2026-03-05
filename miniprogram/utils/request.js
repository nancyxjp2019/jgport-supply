const { getApiBaseUrl } = require('../config/env');

function request({ url, method = 'GET', data = null, withAuth = true, timeout = 15000 }) {
  const app = getApp();
  const token = app.globalData.token || wx.getStorageSync('token') || '';
  const headers = {
    'Content-Type': 'application/json',
  };

  if (withAuth && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${getApiBaseUrl()}${url}`,
      method,
      data,
      timeout,
      header: headers,
      success: (res) => {
        const requestId = (res.header && (res.header['X-Request-ID'] || res.header['x-request-id'])) || '';
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve({
            data: res.data,
            requestId,
            statusCode: res.statusCode,
          });
          return;
        }
        if (res.statusCode === 401) {
          app.globalData.token = '';
          app.globalData.user = null;
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
        }
        reject({
          message: (res.data && res.data.detail) || '请求失败',
          statusCode: res.statusCode,
          requestId,
          raw: res,
        });
      },
      fail: (err) => {
        reject({
          message: err.errMsg || '网络请求失败',
          statusCode: 0,
          requestId: '',
          raw: err,
        });
      },
    });
  });
}

function upload({ url, filePath, name = 'file', formData = {}, withAuth = true }) {
  const app = getApp();
  const token = app.globalData.token || wx.getStorageSync('token') || '';
  const headers = {};
  if (withAuth && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${getApiBaseUrl()}${url}`,
      filePath,
      name,
      formData,
      header: headers,
      success: (res) => {
        const requestId = (res.header && (res.header['X-Request-ID'] || res.header['x-request-id'])) || '';
        let body = {};
        try {
          body = res.data ? JSON.parse(res.data) : {};
        } catch (_error) {
          reject({
            message: '上传响应解析失败',
            statusCode: res.statusCode,
            requestId,
            raw: res,
          });
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve({
            data: body,
            requestId,
            statusCode: res.statusCode,
          });
          return;
        }
        if (res.statusCode === 401) {
          app.globalData.token = '';
          app.globalData.user = null;
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
        }
        reject({
          message: (body && body.detail) || '上传失败',
          statusCode: res.statusCode,
          requestId,
          raw: res,
        });
      },
      fail: (err) => {
        reject({
          message: err.errMsg || '上传失败',
          statusCode: 0,
          requestId: '',
          raw: err,
        });
      },
    });
  });
}

module.exports = {
  request,
  upload,
};
