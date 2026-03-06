const { getRuntimeMode } = require('../config/env');
const { getDemoLightReportOverview } = require('../mocks/report');
const { request } = require('./request');

function sleep(timeout) {
  return new Promise((resolve) => setTimeout(resolve, timeout));
}

async function getLightReportOverview() {
  if (getRuntimeMode() === 'demo') {
    await sleep(120);
    return {
      data: getDemoLightReportOverview(),
      statusCode: 200,
    };
  }

  return request({
    url: '/reports/light/overview',
    method: 'GET',
  });
}

async function getAccessProfile() {
  return request({
    url: '/access/me',
    method: 'GET',
  });
}

async function loginMiniprogramLocal(roleCode) {
  return request({
    url: '/mini-auth/dev-login',
    method: 'POST',
    data: { role_code: roleCode },
    skipAuth: true,
  });
}

module.exports = {
  getAccessProfile,
  getLightReportOverview,
  loginMiniprogramLocal,
};
