import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const inboundListResponse = {
  items: [
    {
      id: 9101,
      doc_no: 'INB-CHAIN-9101',
      contract_id: 5201,
      purchase_order_id: 8101,
      oil_product_id: 'OIL-92',
      warehouse_id: null,
      source_type: 'AUTO_CONTRACT',
      actual_qty: '0.000',
      status: '草稿',
      submitted_at: null,
      created_at: '2026-03-08T09:20:00+08:00',
    },
    {
      id: 9102,
      doc_no: 'INB-CHAIN-9102',
      contract_id: 5202,
      purchase_order_id: 8102,
      oil_product_id: 'OIL-95',
      warehouse_id: 'CODEX-TEST-WH-002',
      source_type: 'AUTO_CONTRACT',
      actual_qty: '106.000',
      status: '校验失败',
      submitted_at: null,
      created_at: '2026-03-08T08:20:00+08:00',
    },
  ],
  total: 2,
  message: 'ok',
}

const inboundDetails = {
  9101: {
    ...inboundListResponse.items[0],
    message: 'ok',
  },
  9102: {
    ...inboundListResponse.items[1],
    message: 'ok',
  },
}

const outboundListResponse = {
  items: [
    {
      id: 9201,
      doc_no: 'OUT-CHAIN-9201',
      contract_id: 4201,
      sales_order_id: 6101,
      oil_product_id: 'OIL-92',
      warehouse_id: 'CODEX-TEST-WH-001',
      source_type: 'SYSTEM',
      source_ticket_no: 'CODEX-TEST-SYS-TICKET-9201',
      manual_ref_no: null,
      actual_qty: '30.000',
      status: '待提交',
      submitted_at: null,
      created_at: '2026-03-08T10:10:00+08:00',
    },
    {
      id: 9202,
      doc_no: 'OUT-CHAIN-9202',
      contract_id: 4202,
      sales_order_id: 6102,
      oil_product_id: 'OIL-95',
      warehouse_id: 'CODEX-TEST-WH-002',
      source_type: 'MANUAL',
      source_ticket_no: null,
      manual_ref_no: 'CODEX-TEST-MANUAL-9202',
      actual_qty: '120.000',
      status: '校验失败',
      submitted_at: null,
      created_at: '2026-03-08T09:25:00+08:00',
    },
    {
      id: 9203,
      doc_no: 'OUT-CHAIN-9203',
      contract_id: 4203,
      sales_order_id: 6103,
      oil_product_id: 'OIL-0',
      warehouse_id: 'CODEX-TEST-WH-003',
      source_type: 'SYSTEM',
      source_ticket_no: 'CODEX-TEST-SYS-TICKET-9203',
      manual_ref_no: null,
      actual_qty: '100.000',
      status: '已过账',
      submitted_at: '2026-03-08T16:50:00+08:00',
      created_at: '2026-03-08T15:55:00+08:00',
    },
  ],
  total: 3,
  message: 'ok',
}

const outboundDetails = {
  9201: {
    ...outboundListResponse.items[0],
    message: 'ok',
  },
  9202: {
    ...outboundListResponse.items[1],
    message: 'ok',
  },
  9203: {
    ...outboundListResponse.items[2],
    message: 'ok',
  },
}

const fetchInboundDocsMock = vi.fn()
const fetchInboundDocDetailMock = vi.fn()
const fetchOutboundDocsMock = vi.fn()
const fetchOutboundDocDetailMock = vi.fn()

const mountOptions = {
  global: {
    directives: {
      loading: () => undefined,
    },
  },
}

vi.mock('@/api/inventory', () => ({
  fetchInboundDocs: fetchInboundDocsMock,
  fetchInboundDocDetail: fetchInboundDocDetailMock,
  fetchOutboundDocs: fetchOutboundDocsMock,
  fetchOutboundDocDetail: fetchOutboundDocDetailMock,
}))

function filterOutboundItems(params?: { status?: string; source_type?: string }) {
  return outboundListResponse.items.filter((item) => {
    if (params?.status && item.status !== params.status) {
      return false
    }
    if (params?.source_type && item.source_type !== params.source_type) {
      return false
    }
    return true
  })
}

describe('InventoryView', () => {
  beforeEach(() => {
    fetchInboundDocsMock.mockReset()
    fetchInboundDocDetailMock.mockReset()
    fetchOutboundDocsMock.mockReset()
    fetchOutboundDocDetailMock.mockReset()

    fetchInboundDocsMock.mockResolvedValue(inboundListResponse)
    fetchInboundDocDetailMock.mockImplementation(async (docId: number) => inboundDetails[docId as 9101 | 9102])
    fetchOutboundDocsMock.mockImplementation(async (params?: { status?: string; source_type?: string }) => {
      const items = filterOutboundItems(params)
      return {
        items,
        total: items.length,
        message: 'ok',
      }
    })
    fetchOutboundDocDetailMock.mockImplementation(async (docId: number) => outboundDetails[docId as 9201 | 9202 | 9203])
  })

  it('挂载后默认加载入库单列表与首条详情', async () => {
    const component = await import('./InventoryView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    expect(fetchInboundDocsMock).toHaveBeenCalledWith({ status: undefined, source_type: undefined })
    expect(fetchInboundDocDetailMock).toHaveBeenCalledWith(9101)
    expect(wrapper.text()).toContain('入库单共 2 条')
    expect(wrapper.text()).toContain('INB-CHAIN-9101')
    expect((wrapper.vm as any).detailHint).toBe('当前单据仍为草稿，通常表示刚生成或刚补录，尚未进入执行提交。')
  }, 10000)

  it('切换到出库单并带筛选刷新列表', async () => {
    const component = await import('./InventoryView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).docType = 'outbound'
    ;(wrapper.vm as any).statusFilter = '校验失败'
    ;(wrapper.vm as any).sourceTypeFilter = 'MANUAL'
    await (wrapper.vm as any).reloadDocs()
    await flushPromises()

    expect(fetchOutboundDocsMock).toHaveBeenLastCalledWith({ status: '校验失败', source_type: 'MANUAL' })
    expect(fetchOutboundDocDetailMock).toHaveBeenLastCalledWith(9202)
    expect(wrapper.text()).toContain('出库单共 1 条')
    expect(wrapper.text()).toContain('OUT-CHAIN-9202')
  }, 10000)

  it('可回看校验失败单据提示与手工回执号展示', async () => {
    const component = await import('./InventoryView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).docType = 'outbound'
    await (wrapper.vm as any).reloadDocs()
    await flushPromises()
    await (wrapper.vm as any).handleCurrentChange(outboundListResponse.items[1])
    await flushPromises()

    expect((wrapper.vm as any).detailHint).toBe('当前单据处于校验失败，请重点核对合同阈值、执行数量与关联订单状态后再继续处理。')
    expect(wrapper.text()).toContain('CODEX-TEST-MANUAL-9202')
    expect(wrapper.text()).toContain('暂无')
  }, 10000)

  it('可区分系统回执与已过账提示', async () => {
    const component = await import('./InventoryView.vue')
    const wrapper = shallowMount(component.default, mountOptions)
    await flushPromises()

    ;(wrapper.vm as any).docType = 'outbound'
    await (wrapper.vm as any).reloadDocs()
    await flushPromises()
    await (wrapper.vm as any).handleCurrentChange(outboundListResponse.items[2])
    await flushPromises()

    expect((wrapper.vm as any).detailHint).toBe('当前单据已过账，执行链路正常。')
    expect(wrapper.text()).toContain('CODEX-TEST-SYS-TICKET-9203')
    expect(wrapper.text()).toContain('首批仅开放追踪与回看，不开放退款核销、批量提交与合同关闭处置动作。')
  }, 10000)
})
