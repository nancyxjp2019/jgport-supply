import type { BoardTasksResponse, DashboardSummaryResponse } from '@/stores/report'

export const demoDashboardSummary: DashboardSummaryResponse = {
  metric_version: 'v1',
  snapshot_time: '2026-03-06T16:20:00+08:00',
  sla_status: '正常',
  contract_execution_rate: '0.852300',
  actual_receipt_today: '650025.00',
  actual_payment_today: '580080.00',
  inventory_turnover_30d: '1.286500',
  threshold_alert_count: 7,
  message: '仪表盘查询成功',
}

export const demoBoardTasks: BoardTasksResponse = {
  metric_version: 'v1',
  snapshot_time: '2026-03-06T16:20:00+08:00',
  sla_status: '正常',
  pending_supplement_count: 3,
  validation_failed_count: 2,
  qty_done_not_closed_count: 2,
  pending_supplement_items: [
    {
      biz_type: 'receipt_doc',
      biz_id: 101,
      title: '收款单 REC-20260306-101 待补录金额',
      status: '待补录金额',
      contract_id: 301,
      contract_no: 'XS-202603-001',
      related_order_id: 501,
      created_at: '2026-03-06T09:20:00+08:00',
    },
    {
      biz_type: 'payment_doc',
      biz_id: 102,
      title: '付款单 PAY-20260306-102 待补录金额',
      status: '待补录金额',
      contract_id: 302,
      contract_no: 'CG-202603-009',
      related_order_id: 502,
      created_at: '2026-03-06T10:15:00+08:00',
    },
  ],
  validation_failed_items: [
    {
      biz_type: 'outbound_doc',
      biz_id: 201,
      title: '出库单 OUT-20260306-201 校验失败',
      status: '校验失败',
      contract_id: 301,
      contract_no: 'XS-202603-001',
      related_order_id: 501,
      created_at: '2026-03-06T11:10:00+08:00',
    },
    {
      biz_type: 'inbound_doc',
      biz_id: 202,
      title: '入库单 INB-20260306-202 校验失败',
      status: '校验失败',
      contract_id: 303,
      contract_no: 'CG-202603-011',
      related_order_id: null,
      created_at: '2026-03-06T13:40:00+08:00',
    },
  ],
  qty_done_not_closed_items: [
    {
      biz_type: 'contract',
      biz_id: 301,
      title: '合同 XS-202603-001 数量履约完成待关闭',
      status: '数量履约完成',
      contract_id: 301,
      contract_no: 'XS-202603-001',
      related_order_id: null,
      created_at: '2026-03-06T14:05:00+08:00',
    },
  ],
  message: '业务看板查询成功',
}
