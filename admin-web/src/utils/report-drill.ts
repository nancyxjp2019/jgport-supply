import type { AdminMultiDimGroupBy, AdminMultiDimReportRow } from '@/api/reports'

import type { LocationQuery, RouteLocationRaw } from 'vue-router'

export type DrillDocType = 'payment' | 'receipt'

const DEFAULT_DRILL_LIMIT = 200
const MAX_DRILL_LIMIT = 1000

interface BaseDrillQuery {
  docType: DrillDocType
  limit: number
  source: string
  drillGroup: string
  drillValue: string
}

export interface FundsRouteQuery extends BaseDrillQuery {
  status: string
}

export interface FundsReconcileRouteQuery extends BaseDrillQuery {
  refundStatus: string
}

export function buildMultiDimDrillRoute(
  groupBy: AdminMultiDimGroupBy,
  row: AdminMultiDimReportRow,
  docType: DrillDocType,
): RouteLocationRaw | null {
  const docCount = docType === 'payment' ? row.payment_doc_count : row.receipt_doc_count
  if (docCount <= 0) {
    return null
  }
  const limit = String(Math.min(Math.max(docCount, DEFAULT_DRILL_LIMIT), MAX_DRILL_LIMIT))
  if (groupBy === 'doc_status') {
    return {
      path: '/funds',
      query: {
        docType,
        status: row.dimension_value,
        limit,
        source: 'reports-multi-dim',
        drillGroup: 'doc_status',
        drillValue: row.dimension_value,
      },
    }
  }
  if (groupBy === 'refund_status') {
    return {
      path: '/funds-reconcile',
      query: {
        docType,
        refundStatus: row.dimension_value,
        limit,
        source: 'reports-multi-dim',
        drillGroup: 'refund_status',
        drillValue: row.dimension_value,
      },
    }
  }
  return null
}

export function parseFundsRouteQuery(query: LocationQuery): FundsRouteQuery {
  return {
    docType: normalizeDocTypeQuery(query.docType),
    status: normalizeQueryValue(query.status),
    limit: normalizeLimitQuery(query.limit),
    source: normalizeQueryValue(query.source),
    drillGroup: normalizeQueryValue(query.drillGroup),
    drillValue: normalizeQueryValue(query.drillValue),
  }
}

export function parseFundsReconcileRouteQuery(query: LocationQuery): FundsReconcileRouteQuery {
  return {
    docType: normalizeDocTypeQuery(query.docType),
    refundStatus: normalizeQueryValue(query.refundStatus),
    limit: normalizeLimitQuery(query.limit),
    source: normalizeQueryValue(query.source),
    drillGroup: normalizeQueryValue(query.drillGroup),
    drillValue: normalizeQueryValue(query.drillValue),
  }
}

export function normalizeQueryValue(value: unknown): string {
  if (Array.isArray(value)) {
    return String(value[0] || '').trim()
  }
  return String(value || '').trim()
}

export function normalizeDocTypeQuery(value: unknown): DrillDocType {
  return normalizeQueryValue(value) === 'receipt' ? 'receipt' : 'payment'
}

export function normalizeLimitQuery(value: unknown): number {
  const parsed = Number(normalizeQueryValue(value))
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return DEFAULT_DRILL_LIMIT
  }
  return Math.min(Math.max(Math.trunc(parsed), 1), MAX_DRILL_LIMIT)
}
