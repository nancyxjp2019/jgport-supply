import { describe, expect, it } from 'vitest'

import type { AdminMultiDimReportRow } from '@/api/reports'

import {
  buildMultiDimDrillRoute,
  parseFundsReconcileRouteQuery,
  parseFundsRouteQuery,
} from '@/utils/report-drill'

const sampleRow: AdminMultiDimReportRow = {
  dimension: 'doc_status',
  dimension_value: '已确认',
  receipt_net_amount: '5000.00',
  payment_net_amount: '3000.00',
  net_cashflow: '2000.00',
  receipt_doc_count: 12,
  payment_doc_count: 8,
  pending_supplement_count: 0,
  refund_pending_review_count: 0,
}

describe('多维报表钻取工具', () => {
  it('可生成 doc_status 钻取到资金处理台的路由', () => {
    const route = buildMultiDimDrillRoute('doc_status', sampleRow, 'receipt')
    expect(route).toMatchObject({
      path: '/funds',
      query: {
        docType: 'receipt',
        status: '已确认',
        source: 'reports-multi-dim',
        drillGroup: 'doc_status',
        drillValue: '已确认',
      },
    })
  })

  it('可生成 refund_status 钻取到退款核销台的路由', () => {
    const refundRow: AdminMultiDimReportRow = {
      ...sampleRow,
      dimension: 'refund_status',
      dimension_value: '待审核',
    }
    const route = buildMultiDimDrillRoute('refund_status', refundRow, 'payment')
    expect(route).toMatchObject({
      path: '/funds-reconcile',
      query: {
        docType: 'payment',
        refundStatus: '待审核',
        source: 'reports-multi-dim',
        drillGroup: 'refund_status',
        drillValue: '待审核',
      },
    })
  })

  it('合同方向维度不生成钻取路由', () => {
    const route = buildMultiDimDrillRoute('contract_direction', sampleRow, 'payment')
    expect(route).toBeNull()
  })

  it('可解析资金处理台钻取路由查询参数', () => {
    const query = parseFundsRouteQuery({
      docType: 'receipt',
      status: '待补录金额',
      limit: '120',
      source: 'reports-multi-dim',
      drillGroup: 'doc_status',
      drillValue: '待补录金额',
    })
    expect(query.docType).toBe('receipt')
    expect(query.status).toBe('待补录金额')
    expect(query.limit).toBe(120)
  })

  it('可解析退款核销台钻取路由查询参数', () => {
    const query = parseFundsReconcileRouteQuery({
      docType: 'payment',
      refundStatus: '待审核',
      limit: '260',
      source: 'reports-multi-dim',
      drillGroup: 'refund_status',
      drillValue: '待审核',
    })
    expect(query.docType).toBe('payment')
    expect(query.refundStatus).toBe('待审核')
    expect(query.limit).toBe(260)
  })
})
