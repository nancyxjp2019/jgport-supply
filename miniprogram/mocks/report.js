const DEMO_LIGHT_REPORT_OVERVIEW = Object.freeze({
  metric_version: 'v1',
  snapshot_time: '2026-03-06T16:20:00+08:00',
  sla_status: '正常',
  actual_receipt_today: '650025.00',
  actual_payment_today: '580080.00',
  inbound_qty_today: '1260.500',
  outbound_qty_today: '1188.000',
  abnormal_count: 3,
  pending_supplement_count: 1,
  validation_failed_count: 1,
  qty_done_not_closed_count: 1,
  message: '轻量报表查询成功',
});

function getDemoLightReportOverview() {
  return {
    ...DEMO_LIGHT_REPORT_OVERVIEW,
  };
}

module.exports = {
  getDemoLightReportOverview,
};
