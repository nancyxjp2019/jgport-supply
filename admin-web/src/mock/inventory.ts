import type {
  InboundDocDetailResponse,
  InboundDocListResponse,
  OutboundDocDetailResponse,
  OutboundDocListResponse,
} from '@/api/inventory'

const DEMO_INBOUND_DOCS: InboundDocDetailResponse[] = [
  {
    id: 9101,
    doc_no: 'INB-DEMO-9101',
    contract_id: 5201,
    purchase_order_id: 91001,
    oil_product_id: 'OIL-92',
    warehouse_id: 'WH-SOUTH-01',
    source_type: 'AUTO_CONTRACT',
    actual_qty: '40.000',
    status: '待提交',
    submitted_at: null,
    created_at: '2026-03-09T09:20:00+08:00',
    message: '演示模式：入库单详情查询成功',
  },
  {
    id: 9102,
    doc_no: 'INB-DEMO-9102',
    contract_id: 5202,
    purchase_order_id: 91002,
    oil_product_id: 'OIL-95',
    warehouse_id: 'WH-NORTH-02',
    source_type: 'AUTO_CONTRACT',
    actual_qty: '106.000',
    status: '校验失败',
    submitted_at: null,
    created_at: '2026-03-09T08:35:00+08:00',
    message: '演示模式：入库单详情查询成功',
  },
  {
    id: 9103,
    doc_no: 'INB-DEMO-9103',
    contract_id: 5203,
    purchase_order_id: null,
    oil_product_id: 'OIL-0',
    warehouse_id: 'WH-SOUTH-01',
    source_type: 'AUTO_CONTRACT',
    actual_qty: '100.000',
    status: '已过账',
    submitted_at: '2026-03-08T17:10:00+08:00',
    created_at: '2026-03-08T16:20:00+08:00',
    message: '演示模式：入库单详情查询成功',
  },
]

const DEMO_OUTBOUND_DOCS: OutboundDocDetailResponse[] = [
  {
    id: 9201,
    doc_no: 'OUT-DEMO-9201',
    contract_id: 4201,
    sales_order_id: 6101,
    oil_product_id: 'OIL-92',
    warehouse_id: 'WH-SOUTH-01',
    source_type: 'SYSTEM',
    source_ticket_no: 'AUTO-TEST-SYS-TICKET-9201',
    manual_ref_no: null,
    actual_qty: '30.000',
    status: '待提交',
    submitted_at: null,
    created_at: '2026-03-09T09:10:00+08:00',
    message: '演示模式：出库单详情查询成功',
  },
  {
    id: 9202,
    doc_no: 'OUT-DEMO-9202',
    contract_id: 4202,
    sales_order_id: 6102,
    oil_product_id: 'OIL-95',
    warehouse_id: 'WH-NORTH-02',
    source_type: 'MANUAL',
    source_ticket_no: null,
    manual_ref_no: 'AUTO-TEST-MANUAL-9202',
    actual_qty: '120.000',
    status: '校验失败',
    submitted_at: null,
    created_at: '2026-03-09T08:25:00+08:00',
    message: '演示模式：出库单详情查询成功',
  },
  {
    id: 9203,
    doc_no: 'OUT-DEMO-9203',
    contract_id: 4203,
    sales_order_id: 6103,
    oil_product_id: 'OIL-0',
    warehouse_id: 'WH-SOUTH-01',
    source_type: 'SYSTEM',
    source_ticket_no: 'AUTO-TEST-SYS-TICKET-9203',
    manual_ref_no: null,
    actual_qty: '100.000',
    status: '已过账',
    submitted_at: '2026-03-08T16:50:00+08:00',
    created_at: '2026-03-08T15:55:00+08:00',
    message: '演示模式：出库单详情查询成功',
  },
]

function cloneInboundDoc(item: InboundDocDetailResponse): InboundDocDetailResponse {
  return { ...item }
}

function cloneOutboundDoc(item: OutboundDocDetailResponse): OutboundDocDetailResponse {
  return { ...item }
}

export function listDemoInboundDocs(params?: {
  status?: string
  source_type?: string
}): InboundDocListResponse {
  const normalizedStatus = String(params?.status || '').trim()
  const normalizedSourceType = String(params?.source_type || '').trim()
  const filtered = DEMO_INBOUND_DOCS.filter((item) => {
    if (normalizedStatus && item.status !== normalizedStatus) {
      return false
    }
    if (normalizedSourceType && item.source_type !== normalizedSourceType) {
      return false
    }
    return true
  })
  return {
    items: filtered.map(cloneInboundDoc),
    total: filtered.length,
    message: '演示模式：入库单列表查询成功',
  }
}

export function listDemoOutboundDocs(params?: {
  status?: string
  source_type?: string
}): OutboundDocListResponse {
  const normalizedStatus = String(params?.status || '').trim()
  const normalizedSourceType = String(params?.source_type || '').trim()
  const filtered = DEMO_OUTBOUND_DOCS.filter((item) => {
    if (normalizedStatus && item.status !== normalizedStatus) {
      return false
    }
    if (normalizedSourceType && item.source_type !== normalizedSourceType) {
      return false
    }
    return true
  })
  return {
    items: filtered.map(cloneOutboundDoc),
    total: filtered.length,
    message: '演示模式：出库单列表查询成功',
  }
}

export function getDemoInboundDocDetail(docId: number): InboundDocDetailResponse {
  const target = DEMO_INBOUND_DOCS.find((item) => item.id === Number(docId))
  if (!target) {
    throw new Error('当前入库单不存在，请刷新后重试')
  }
  return cloneInboundDoc(target)
}

export function getDemoOutboundDocDetail(docId: number): OutboundDocDetailResponse {
  const target = DEMO_OUTBOUND_DOCS.find((item) => item.id === Number(docId))
  if (!target) {
    throw new Error('当前出库单不存在，请刷新后重试')
  }
  return cloneOutboundDoc(target)
}
