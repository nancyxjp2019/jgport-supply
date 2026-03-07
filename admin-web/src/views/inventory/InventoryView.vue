<template>
  <div class="page-stack inventory-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <section class="panel-card inventory-filter-card">
      <div class="inventory-filter-row">
        <div>
          <p class="panel-card__eyebrow">库存与执行跟踪台首批</p>
          <h3>入库单 / 出库单执行跟踪</h3>
          <p>首批支持单据追踪、校验失败回看与执行异常提示，不开放批量处理与关闭处置。</p>
        </div>
        <div class="inventory-filter-actions">
          <ElSelect v-model="docType" class="inventory-filter-select" @change="reloadDocs">
            <ElOption v-for="item in docTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="statusFilter" class="inventory-filter-select" placeholder="全部状态" clearable @change="reloadDocs">
            <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="sourceTypeFilter" class="inventory-filter-select" placeholder="全部来源" clearable @change="reloadDocs">
            <ElOption v-for="item in sourceTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElButton type="primary" :loading="loading" @click="reloadDocs">刷新列表</ElButton>
        </div>
      </div>
    </section>

    <section class="inventory-main-grid">
      <article class="panel-card inventory-list-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">执行单据列表</p>
            <h3>{{ currentDocTypeLabel }}共 {{ docList.length }} 条</h3>
          </div>
          <span>按创建时间倒序</span>
        </header>

        <ElTable
          v-loading="loading"
          :data="docList"
          row-key="id"
          highlight-current-row
          :row-class-name="resolveDocRowClass"
          @current-change="handleCurrentChange"
        >
          <ElTableColumn prop="doc_no" label="单据号" min-width="160" />
          <ElTableColumn prop="contract_id" label="合同ID" min-width="120" />
          <ElTableColumn :label="relatedOrderLabel" min-width="130">
            <template #default="scope">
              {{ resolveRelatedOrderId(scope.row) }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="oil_product_id" label="油品" min-width="110" />
          <ElTableColumn prop="source_type" label="来源" min-width="110" />
          <ElTableColumn label="数量" min-width="120">
            <template #default="scope">
              {{ formatQty(scope.row.actual_qty) }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="status" label="状态" min-width="120" />
          <ElTableColumn label="创建时间" min-width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.created_at) }}
            </template>
          </ElTableColumn>
        </ElTable>
      </article>

      <article class="panel-card inventory-detail-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">执行详情</p>
            <h3>{{ selectedDoc?.doc_no || '未选择单据' }}</h3>
          </div>
          <span v-if="selectedDoc">{{ selectedDoc.status }}</span>
        </header>

        <ElEmpty v-if="!selectedDoc" description="请选择一条执行单据查看详情" />

        <template v-else>
          <div class="inventory-detail-grid">
            <div class="detail-row">
              <span>单据来源</span>
              <strong>{{ selectedDoc.source_type }}</strong>
            </div>
            <div class="detail-row">
              <span>合同ID</span>
              <strong>{{ selectedDoc.contract_id }}</strong>
            </div>
            <div class="detail-row">
              <span>{{ relatedOrderLabel }}</span>
              <strong>{{ resolveRelatedOrderId(selectedDoc) }}</strong>
            </div>
            <div class="detail-row">
              <span>油品</span>
              <strong>{{ selectedDoc.oil_product_id }}</strong>
            </div>
            <div class="detail-row">
              <span>仓库</span>
              <strong>{{ selectedDoc.warehouse_id || '未填写' }}</strong>
            </div>
            <div class="detail-row">
              <span>实际数量</span>
              <strong>{{ formatQty(selectedDoc.actual_qty) }}</strong>
            </div>
            <div class="detail-row" v-if="docType === 'outbound'">
              <span>系统回执号</span>
              <strong>{{ resolveSourceTicketNo(selectedDoc) }}</strong>
            </div>
            <div class="detail-row" v-if="docType === 'outbound'">
              <span>手工回执号</span>
              <strong>{{ resolveManualRefNo(selectedDoc) }}</strong>
            </div>
            <div class="detail-row">
              <span>提交时间</span>
              <strong>{{ formatDateTime(selectedDoc.submitted_at) }}</strong>
            </div>
          </div>

          <div class="inventory-alert-panel" :class="`is-${detailSeverity}`">
            <p class="inventory-alert-title">执行异常提示</p>
            <p>{{ detailHint }}</p>
          </div>
          <p class="order-boundary-tip">首批仅开放追踪与回看，不开放退款核销、批量提交与合同关闭处置动作。</p>
        </template>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  ElAlert,
  ElButton,
  ElEmpty,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
} from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import {
  fetchInboundDocDetail,
  fetchInboundDocs,
  fetchOutboundDocDetail,
  fetchOutboundDocs,
  type InboundDocDetailResponse,
  type InboundDocListItem,
  type OutboundDocDetailResponse,
  type OutboundDocListItem,
} from '@/api/inventory'
import { formatDateTime, formatQty } from '@/utils/formatters'

type InventoryDocType = 'inbound' | 'outbound'
type InventoryDocListItem = InboundDocListItem | OutboundDocListItem
type InventoryDocDetail = InboundDocDetailResponse | OutboundDocDetailResponse

const docTypeOptions: Array<{ label: string; value: InventoryDocType }> = [
  { label: '入库单', value: 'inbound' },
  { label: '出库单', value: 'outbound' },
]
const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '草稿', value: '草稿' },
  { label: '待提交', value: '待提交' },
  { label: '校验失败', value: '校验失败' },
  { label: '已过账', value: '已过账' },
  { label: '已终止', value: '已终止' },
]

const loading = ref(false)
const errorMessage = ref('')
const docType = ref<InventoryDocType>('inbound')
const statusFilter = ref('')
const sourceTypeFilter = ref('')
const docList = ref<InventoryDocListItem[]>([])
const selectedDocId = ref<number | null>(null)
const selectedDoc = ref<InventoryDocDetail | null>(null)

const currentDocTypeLabel = computed(() => (docType.value === 'inbound' ? '入库单' : '出库单'))
const relatedOrderLabel = computed(() => (docType.value === 'inbound' ? '采购订单ID' : '销售订单ID'))
const sourceTypeOptions = computed(() =>
  docType.value === 'inbound'
    ? [{ label: '全部来源', value: '' }, { label: '自动合同生成', value: 'AUTO_CONTRACT' }]
    : [
      { label: '全部来源', value: '' },
      { label: '仓库正常流程', value: 'SYSTEM' },
      { label: '手工补录', value: 'MANUAL' },
    ],
)

const detailSeverity = computed(() => {
  if (!selectedDoc.value) {
    return 'neutral'
  }
  if (selectedDoc.value.status === '校验失败') {
    return 'danger'
  }
  if (selectedDoc.value.status === '已终止') {
    return 'warning'
  }
  if (selectedDoc.value.status === '待提交' || selectedDoc.value.status === '草稿') {
    return 'info'
  }
  return 'success'
})

const detailHint = computed(() => {
  if (!selectedDoc.value) {
    return '请选择一条执行单据查看风险提示。'
  }
  if (selectedDoc.value.status === '校验失败') {
    return '当前单据处于校验失败，请重点核对合同阈值、执行数量与关联订单状态后再继续处理。'
  }
  if (selectedDoc.value.status === '已终止') {
    return '当前单据已终止，通常由合同数量履约完成触发，请转合同关闭与差异处理台继续回看。'
  }
  if (selectedDoc.value.status === '待提交') {
    return '当前单据待提交，请确认仓库、数量与来源回执信息完整后推进到过账。'
  }
  if (selectedDoc.value.status === '草稿') {
    return '当前单据仍为草稿，通常表示刚生成或刚补录，尚未进入执行提交。'
  }
  return '当前单据已过账，执行链路正常。'
})

function resolveDocRowClass(params: { row: InventoryDocListItem }) {
  return params.row.id === selectedDocId.value ? 'is-selected-order-row' : ''
}

function resolveRelatedOrderId(item: InventoryDocListItem | InventoryDocDetail): number | string {
  if (docType.value === 'inbound') {
    const inboundItem = item as InboundDocListItem
    return inboundItem.purchase_order_id || '未绑定'
  }
  const outboundItem = item as OutboundDocListItem
  return outboundItem.sales_order_id || '未绑定'
}

function resolveSourceTicketNo(item: InventoryDocDetail | null): string {
  if (!item || docType.value !== 'outbound') {
    return '暂无'
  }
  return (item as OutboundDocDetailResponse).source_ticket_no || '暂无'
}

function resolveManualRefNo(item: InventoryDocDetail | null): string {
  if (!item || docType.value !== 'outbound') {
    return '暂无'
  }
  return (item as OutboundDocDetailResponse).manual_ref_no || '暂无'
}

async function loadDocs(preferredId?: number) {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = docType.value === 'inbound'
      ? await fetchInboundDocs({
        status: statusFilter.value || undefined,
        source_type: sourceTypeFilter.value || undefined,
      })
      : await fetchOutboundDocs({
        status: statusFilter.value || undefined,
        source_type: sourceTypeFilter.value || undefined,
      })
    docList.value = response.items
    if (!docList.value.length) {
      selectedDocId.value = null
      selectedDoc.value = null
      return
    }
    const nextId = preferredId && docList.value.some((item) => item.id === preferredId)
      ? preferredId
      : selectedDocId.value && docList.value.some((item) => item.id === selectedDocId.value)
        ? selectedDocId.value
        : docList.value[0].id
    selectedDocId.value = nextId
    await loadDetail(nextId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '执行单据列表加载失败'
  } finally {
    loading.value = false
  }
}

async function reloadDocs() {
  await loadDocs()
}

async function loadDetail(docId: number) {
  try {
    selectedDoc.value = docType.value === 'inbound'
      ? await fetchInboundDocDetail(docId)
      : await fetchOutboundDocDetail(docId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '执行单据详情加载失败'
    selectedDoc.value = null
  }
}

async function handleCurrentChange(row: InventoryDocListItem | null) {
  if (!row) {
    return
  }
  selectedDocId.value = row.id
  await loadDetail(row.id)
}

onMounted(async () => {
  await loadDocs()
})
</script>
