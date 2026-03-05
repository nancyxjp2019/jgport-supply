const { upload } = require('./request');

function buildAbsoluteUrl(rawUrl) {
  const value = String(rawUrl || '').trim();
  if (!value) {
    return '';
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  const app = getApp();
  const apiBase = (app.globalData && app.globalData.apiBaseUrl) || '';
  const origin = apiBase.replace(/\/api\/v1\/?$/, '');
  if (!origin) {
    return value;
  }
  if (value.startsWith('/')) {
    return `${origin}${value}`;
  }
  return `${origin}/${value}`;
}

function buildDownloadHeaders() {
  const app = getApp();
  const token = (app.globalData && app.globalData.token) || wx.getStorageSync('token') || '';
  if (!token) {
    return {};
  }
  return {
    Authorization: `Bearer ${token}`,
  };
}

function isUsableMiniProgramFilePath(filePath) {
  const normalized = String(filePath || '').trim();
  const userDataPath = (wx.env && wx.env.USER_DATA_PATH) || '';
  if (!normalized) {
    return false;
  }
  return normalized.startsWith('wxfile://') || (userDataPath ? normalized.startsWith(userDataPath) : false);
}

function downloadRemoteFile(url) {
  // 不指定 filePath，让微信使用临时目录（wxfile://tmp_...）
  // 若指定 filePath 会保存到用户目录（wxfile://usr/...），
  // 导致 fs.saveFile 无法接受用户目录路径，且旧版微信（< 2.12.0）
  // 的 wx.openDocument 不支持打开用户目录文件，从而使所有报表无法打开。
  const targetUrl = buildAbsoluteUrl(url);
  return new Promise((resolve, reject) => {
    wx.downloadFile({
      url: targetUrl,
      header: buildDownloadHeaders(),
      success: resolve,
      fail: reject,
    });
  });
}

function requestRemoteBinary(url) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: buildAbsoluteUrl(url),
      method: 'GET',
      responseType: 'arraybuffer',
      header: buildDownloadHeaders(),
      success: resolve,
      fail: reject,
    });
  });
}

function buildRetryDownloadFilePath(fileName, fileType) {
  const userDataPath = wx.env && wx.env.USER_DATA_PATH;
  if (!userDataPath) {
    return '';
  }
  const hintedExtension = extractNormalizedExtension(fileName);
  const normalizedExtension = hintedExtension || String(fileType || '').trim().toLowerCase() || 'bin';
  const suffix = normalizedExtension ? `.${normalizedExtension}` : '';
  return `${userDataPath}/open-${Date.now()}-${Math.random().toString(16).slice(2)}${suffix}`;
}

function downloadRemoteFileToUserData(url, fileName, fileType) {
  const targetUrl = buildAbsoluteUrl(url);
  const retryFilePath = buildRetryDownloadFilePath(fileName, fileType);
  if (!targetUrl || !retryFilePath) {
    return Promise.reject(new Error('下载重试失败'));
  }
  return new Promise((resolve, reject) => {
    wx.downloadFile({
      url: targetUrl,
      filePath: retryFilePath,
      header: buildDownloadHeaders(),
      success: (res) => {
        const downloadedPath = String((res && (res.filePath || res.tempFilePath)) || retryFilePath).trim();
        if (!res || res.statusCode < 200 || res.statusCode >= 300 || !downloadedPath) {
          reject(res || new Error('下载重试失败'));
          return;
        }
        const resolvedFilePath = isUsableMiniProgramFilePath(downloadedPath) ? downloadedPath : retryFilePath;
        resolve({
          downloadedFilePath: downloadedPath,
          requestedFilePath: retryFilePath,
          resolvedFilePath,
          statusCode: res.statusCode,
        });
      },
      fail: reject,
    });
  });
}

function isImageFile(url, fileName = '', contentType = '') {
  const urlExtension = extractNormalizedExtension(url);
  const fileNameExtension = extractNormalizedExtension(fileName);
  const supportedImageTypes = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'];
  if (supportedImageTypes.includes(urlExtension) || supportedImageTypes.includes(fileNameExtension)) {
    return true;
  }
  return String(contentType || '').trim().toLowerCase().startsWith('image/');
}

function extractNormalizedExtension(value) {
  const normalized = String(value || '').trim().split('?')[0].split('#')[0].toLowerCase();
  const extension = normalized.includes('.') ? normalized.slice(normalized.lastIndexOf('.') + 1) : '';
  return extension;
}

function mapContentTypeToFileType(contentType = '') {
  const normalized = String(contentType || '').trim().toLowerCase();
  if (!normalized) {
    return '';
  }
  if (normalized.includes('spreadsheetml.sheet')) {
    return 'xlsx';
  }
  if (normalized.includes('ms-excel')) {
    return 'xls';
  }
  if (normalized.includes('pdf')) {
    return 'pdf';
  }
  if (normalized.includes('wordprocessingml.document')) {
    return 'docx';
  }
  if (normalized.includes('msword')) {
    return 'doc';
  }
  if (normalized.includes('presentationml.presentation')) {
    return 'pptx';
  }
  if (normalized.includes('ms-powerpoint')) {
    return 'ppt';
  }
  return '';
}

function inferDocumentFileType(url, fileName = '', contentType = '') {
  const extension = extractNormalizedExtension(fileName) || extractNormalizedExtension(url);
  const supportedTypes = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'];
  if (supportedTypes.includes(extension)) {
    return extension;
  }
  const mappedType = mapContentTypeToFileType(contentType);
  return supportedTypes.includes(mappedType) ? mappedType : '';
}

function getHeaderValue(headers, headerName) {
  if (!headers || typeof headers !== 'object') {
    return '';
  }
  const matchedKey = Object.keys(headers).find((key) => String(key || '').toLowerCase() === String(headerName || '').toLowerCase());
  return matchedKey ? String(headers[matchedKey] || '').trim() : '';
}

function decodeMaybeEncodedText(value) {
  const text = String(value || '').trim();
  if (!text) {
    return '';
  }
  try {
    return decodeURIComponent(text);
  } catch (_error) {
    return text;
  }
}

function extractFileNameFromDisposition(headers) {
  const disposition = getHeaderValue(headers, 'content-disposition');
  if (!disposition) {
    return '';
  }
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    return decodeMaybeEncodedText(utf8Match[1]);
  }
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  return plainMatch && plainMatch[1] ? decodeMaybeEncodedText(plainMatch[1]) : '';
}

function writeBinaryFile(filePath, data) {
  if (!filePath || typeof wx.getFileSystemManager !== 'function') {
    return Promise.reject(new Error('写入文件失败'));
  }
  const fs = wx.getFileSystemManager();
  if (!fs || typeof fs.writeFile !== 'function') {
    return Promise.reject(new Error('写入文件失败'));
  }
  return new Promise((resolve, reject) => {
    fs.writeFile({
      filePath,
      data,
      success: () => resolve(filePath),
      fail: reject,
    });
  });
}

function isRemoteLikePath(filePath) {
  return /^https?:\/\//i.test(String(filePath || '').trim());
}

function isTempMiniProgramFilePath(filePath) {
  const normalized = String(filePath || '').trim().toLowerCase();
  return normalized.startsWith('wxfile://tmp') || normalized.startsWith('http://tmp/');
}

function resolveDownloadedFilePath(downloadRes) {
  const directFilePath = String((downloadRes && downloadRes.filePath) || '').trim();
  if (directFilePath && isUsableMiniProgramFilePath(directFilePath)) {
    return directFilePath;
  }
  const requestedFilePath = String((downloadRes && downloadRes.requestedFilePath) || '').trim();
  if (requestedFilePath && isUsableMiniProgramFilePath(requestedFilePath)) {
    return requestedFilePath;
  }
  const tempFilePath = String((downloadRes && downloadRes.tempFilePath) || '').trim();
  if (tempFilePath && isUsableMiniProgramFilePath(tempFilePath)) {
    return tempFilePath;
  }
  return directFilePath || requestedFilePath || tempFilePath;
}

async function materializeRemoteFileByRequest(url, fileName, fileType) {
  const requestRes = await requestRemoteBinary(url);
  if (!requestRes || requestRes.statusCode < 200 || requestRes.statusCode >= 300 || !requestRes.data) {
    throw new Error('二进制请求失败');
  }
  const responseContentType = getHeaderValue(requestRes.header, 'content-type');
  const responseFileName = extractFileNameFromDisposition(requestRes.header) || decodeMaybeEncodedText(getHeaderValue(requestRes.header, 'x-file-name'));
  const resolvedFileName = String(fileName || responseFileName || '').trim();
  const resolvedFileType = inferDocumentFileType(url, resolvedFileName, responseContentType) || fileType || 'tmp';
  const localFilePath = buildRetryDownloadFilePath(resolvedFileName, resolvedFileType);
  if (!localFilePath) {
    throw new Error('本地落地路径不可用');
  }
  await writeBinaryFile(localFilePath, requestRes.data);
  return {
    filePath: localFilePath,
    statusCode: requestRes.statusCode,
    responseContentType,
    responseFileName,
  };
}

function saveTempFile(filePath) {
  if (!filePath || typeof wx.getFileSystemManager !== 'function') {
    return Promise.reject(new Error('保存文件失败'));
  }
  const fs = wx.getFileSystemManager();
  if (!fs || typeof fs.saveFile !== 'function') {
    return Promise.reject(new Error('保存文件失败'));
  }
  return new Promise((resolve, reject) => {
    fs.saveFile({
      tempFilePath: filePath,
      success: (res) => resolve(res.savedFilePath || filePath),
      fail: reject,
    });
  });
}

async function buildOpenDocumentPaths(filePath) {
  const paths = [];
  const pathBuildErrors = [];
  const pushPath = (value) => {
    const path = String(value || '').trim();
    if (!path || paths.includes(path)) {
      return;
    }
    paths.push(path);
  };
  if (!isUsableMiniProgramFilePath(filePath)) {
    pathBuildErrors.push({
      stage: 'validateFilePath',
      error: {
        message: '下载结果未返回可用本地路径',
      },
    });
    return {
      candidatePaths: paths,
      pathBuildErrors,
    };
  }
  pushPath(filePath);
  if (isTempMiniProgramFilePath(filePath)) {
    try {
      const savedFilePath = await saveTempFile(filePath);
      pushPath(savedFilePath);
    } catch (error) {
      pathBuildErrors.push({
        stage: 'saveFile',
        error: simplifyMiniProgramError(error),
      });
    }
  }
  return {
    candidatePaths: paths,
    pathBuildErrors,
  };
}

function openDocumentByPath(filePath, fileType) {
  return new Promise((resolve, reject) => {
    const options = {
      filePath,
      showMenu: true,
      success: resolve,
      fail: reject,
    };
    if (fileType) {
      options.fileType = fileType;
    }
    wx.openDocument(options);
  });
}

function previewImageByPath(filePath) {
  return new Promise((resolve, reject) => {
    wx.previewImage({
      current: filePath,
      urls: [filePath],
      success: resolve,
      fail: reject,
    });
  });
}

function getImageInfoByPath(filePath) {
  return new Promise((resolve, reject) => {
    wx.getImageInfo({
      src: filePath,
      success: resolve,
      fail: reject,
    });
  });
}

function pushUniquePath(paths, value) {
  const normalizedValue = String(value || '').trim();
  if (!normalizedValue || paths.includes(normalizedValue)) {
    return;
  }
  paths.push(normalizedValue);
}

function simplifyMiniProgramError(error) {
  if (!error) {
    return { message: 'unknown_error' };
  }
  if (typeof error === 'string') {
    return { message: error };
  }
  const message = String(error.errMsg || error.message || 'unknown_error').trim();
  const detail = { message };
  if (error.errno !== undefined && error.errno !== null) {
    detail.errno = error.errno;
  }
  if (error.code !== undefined && error.code !== null) {
    detail.code = error.code;
  }
  return detail;
}

function stringifyDiagnostics(diagnostics) {
  try {
    return JSON.stringify(diagnostics, null, 2);
  } catch (_error) {
    return '[diagnostics_unserializable]';
  }
}

function resolvePrimaryErrorMessage(diagnostics) {
  if (!diagnostics || typeof diagnostics !== 'object') {
    return '';
  }
  const finalMessage = diagnostics.finalError && diagnostics.finalError.message;
  if (finalMessage) {
    return String(finalMessage).trim();
  }
  const previewMessage = diagnostics.previewError && diagnostics.previewError.message;
  if (previewMessage) {
    return String(previewMessage).trim();
  }
  if (Array.isArray(diagnostics.openAttempts) && diagnostics.openAttempts.length) {
    const attemptMessage = diagnostics.openAttempts[diagnostics.openAttempts.length - 1].error
      && diagnostics.openAttempts[diagnostics.openAttempts.length - 1].error.message;
    if (attemptMessage) {
      return String(attemptMessage).trim();
    }
  }
  return '';
}

function logFileOpenDiagnostics(tag, diagnostics) {
  try {
    console.error(`[文件打开诊断] ${tag}`, diagnostics);
    console.error(`[文件打开诊断JSON] ${tag}\n${stringifyDiagnostics(diagnostics)}`);
  } catch (_error) {
  }
}

function buildOpenFailureError(tag, diagnostics) {
  logFileOpenDiagnostics(tag, diagnostics);
  const detailMessage = resolvePrimaryErrorMessage(diagnostics);
  const error = new Error(detailMessage ? `文件打开失败：${detailMessage}` : '文件打开失败，请在控制台搜索“文件打开诊断”查看详情');
  error.diagnostics = diagnostics;
  return error;
}

function openRemoteFile(url, options = {}) {
  const targetUrl = buildAbsoluteUrl(url);
  if (!targetUrl) {
    return Promise.reject(new Error('暂无文件'));
  }
  const hintedFileName = String(options.fileName || '').trim();
  return downloadRemoteFile(targetUrl)
    .then(async (res) => {
      const downloadedFilePath = resolveDownloadedFilePath(res);
      if (!res || res.statusCode < 200 || res.statusCode >= 300 || !downloadedFilePath) {
        throw buildOpenFailureError('下载失败', {
          url: targetUrl,
          statusCode: res && res.statusCode,
          tempFilePath: res && res.tempFilePath,
          filePath: res && res.filePath,
          requestedFilePath: res && res.requestedFilePath,
          downloadedFilePath,
          headers: (res && res.header) || {},
        });
      }
      const responseFileName = extractFileNameFromDisposition(res.header) || decodeMaybeEncodedText(getHeaderValue(res.header, 'x-file-name'));
      const responseContentType = getHeaderValue(res.header, 'content-type');
      const fileName = String(responseFileName || hintedFileName || '').trim();
      const fileType = inferDocumentFileType(targetUrl, fileName, responseContentType);
      const diagnostics = {
        url: targetUrl,
        fileName,
        statusCode: res.statusCode,
        responseContentType,
        tempFilePath: res.tempFilePath,
        filePath: res.filePath,
        requestedFilePath: res.requestedFilePath,
        downloadedFilePath,
        headers: {
          contentDisposition: getHeaderValue(res.header, 'content-disposition'),
          xFileName: getHeaderValue(res.header, 'x-file-name'),
          contentType: responseContentType,
        },
      };
      let resolvedFilePath = downloadedFilePath;
      if (!isUsableMiniProgramFilePath(resolvedFilePath) || isRemoteLikePath(resolvedFilePath)) {
        try {
          const requestFallback = await materializeRemoteFileByRequest(targetUrl, fileName, fileType);
          resolvedFilePath = requestFallback.filePath;
          diagnostics.requestFallback = {
            used: true,
            filePath: requestFallback.filePath,
            statusCode: requestFallback.statusCode,
            responseContentType: requestFallback.responseContentType,
            responseFileName: requestFallback.responseFileName,
          };
        } catch (error) {
          diagnostics.requestFallbackError = simplifyMiniProgramError(error);
        }
      }
      if (isImageFile(targetUrl, fileName, responseContentType)) {
        const previewAttempts = [];
        const previewCandidatePaths = [];
        const imageInfoAttempts = [];
        pushUniquePath(previewCandidatePaths, resolvedFilePath);
        pushUniquePath(previewCandidatePaths, downloadedFilePath);

        for (let index = 0; index < previewCandidatePaths.length; index += 1) {
          const candidatePath = previewCandidatePaths[index];
          try {
            const imageInfo = await getImageInfoByPath(candidatePath);
            const previewPath = String((imageInfo && imageInfo.path) || candidatePath).trim() || candidatePath;
            imageInfoAttempts.push({
              path: candidatePath,
              normalizedPath: previewPath,
              type: String((imageInfo && imageInfo.type) || '').trim(),
              width: Number((imageInfo && imageInfo.width) || 0),
              height: Number((imageInfo && imageInfo.height) || 0),
            });
            return await previewImageByPath(previewPath);
          } catch (error) {
            previewAttempts.push({
              path: candidatePath,
              mode: 'direct-preview',
              error: simplifyMiniProgramError(error),
            });
          }
        }

        try {
          const retryResult = await downloadRemoteFileToUserData(targetUrl, fileName, fileType || extractNormalizedExtension(fileName) || 'png');
          diagnostics.retryDownloadedFilePath = retryResult.downloadedFilePath;
          diagnostics.retryRequestedFilePath = retryResult.requestedFilePath;
          const retryPreviewPath = String(retryResult.resolvedFilePath || retryResult.requestedFilePath || retryResult.downloadedFilePath || '').trim();
          if (retryPreviewPath) {
            try {
              const imageInfo = await getImageInfoByPath(retryPreviewPath);
              const normalizedRetryPreviewPath = String((imageInfo && imageInfo.path) || retryPreviewPath).trim() || retryPreviewPath;
              imageInfoAttempts.push({
                path: retryPreviewPath,
                normalizedPath: normalizedRetryPreviewPath,
                type: String((imageInfo && imageInfo.type) || '').trim(),
                width: Number((imageInfo && imageInfo.width) || 0),
                height: Number((imageInfo && imageInfo.height) || 0),
              });
              return await previewImageByPath(normalizedRetryPreviewPath);
            } catch (error) {
              previewAttempts.push({
                path: retryPreviewPath,
                mode: 'retry-download-preview',
                error: simplifyMiniProgramError(error),
              });
            }
          }
        } catch (error) {
          diagnostics.retryDownloadError = simplifyMiniProgramError(error);
        }

        throw buildOpenFailureError('图片预览失败', {
          ...diagnostics,
          mode: 'image-preview',
          resolvedFilePath,
          imageInfoAttempts,
          previewAttempts,
          previewError: previewAttempts.length ? previewAttempts[previewAttempts.length - 1].error : { message: '图片预览失败' },
        });
      }
      const pathResult = await buildOpenDocumentPaths(resolvedFilePath);
      const candidatePaths = pathResult.candidatePaths;
      const openAttempts = [];
      let lastError = null;
      for (let index = 0; index < candidatePaths.length; index += 1) {
        const candidatePath = candidatePaths[index];
        if (fileType) {
          try {
            return await openDocumentByPath(candidatePath, fileType);
          } catch (error) {
            lastError = error;
            openAttempts.push({
              path: candidatePath,
              mode: `with-file-type:${fileType}`,
              error: simplifyMiniProgramError(error),
            });
          }
        }
        try {
          return await openDocumentByPath(candidatePath);
        } catch (error) {
          lastError = error;
          openAttempts.push({
            path: candidatePath,
            mode: 'without-file-type',
            error: simplifyMiniProgramError(error),
          });
        }
      }
      const shouldRetryDownloadToUserData = !candidatePaths.some((item) => isUsableMiniProgramFilePath(item))
        || openAttempts.some((item) => /no such file or directory/i.test(String((item.error && item.error.message) || '')));
      if (shouldRetryDownloadToUserData) {
        try {
          const retryResult = await downloadRemoteFileToUserData(targetUrl, fileName, fileType);
          diagnostics.retryDownloadedFilePath = retryResult.downloadedFilePath;
          diagnostics.retryRequestedFilePath = retryResult.requestedFilePath;
          const retryPath = String(retryResult.resolvedFilePath || retryResult.requestedFilePath || retryResult.downloadedFilePath || '').trim();
          if (retryPath) {
            if (fileType) {
              try {
                return await openDocumentByPath(retryPath, fileType);
              } catch (error) {
                lastError = error;
                openAttempts.push({
                  path: retryPath,
                  mode: `retry-download-with-file-type:${fileType}`,
                  error: simplifyMiniProgramError(error),
                });
              }
            }
            try {
              return await openDocumentByPath(retryPath);
            } catch (error) {
              lastError = error;
              openAttempts.push({
                path: retryPath,
                mode: 'retry-download-without-file-type',
                error: simplifyMiniProgramError(error),
              });
            }
          }
        } catch (error) {
          diagnostics.retryDownloadError = simplifyMiniProgramError(error);
        }
      }
      throw buildOpenFailureError('文档打开失败', {
        ...diagnostics,
        mode: 'document-open',
        fileType,
        resolvedFilePath,
        candidatePaths,
        pathBuildErrors: pathResult.pathBuildErrors,
        openAttempts,
        finalError: simplifyMiniProgramError(lastError),
      });
    });
}

function chooseAndUploadFile(category = 'general') {
  return new Promise((resolve, reject) => {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'jpg', 'jpeg', 'png', 'webp', 'xls', 'xlsx'],
      success: async (res) => {
        try {
          const selected = res.tempFiles && res.tempFiles[0];
          if (!selected || !selected.path) {
            reject(new Error('未选择文件'));
            return;
          }
          const uploadRes = await upload({
            url: '/files/upload',
            filePath: selected.path,
            name: 'file',
            formData: { category },
          });
          resolve(uploadRes.data);
        } catch (error) {
          reject(error);
        }
      },
      fail: reject,
    });
  });
}

module.exports = {
  buildAbsoluteUrl,
  chooseAndUploadFile,
  openRemoteFile,
};
