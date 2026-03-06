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

module.exports = {
  getLightReportOverview,
};
