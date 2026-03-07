<template>
  <div class="page-stack funds-reconcile-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <section class="panel-card funds-reconcile-filter-card">
      <div class="funds-reconcile-filter-row">
        <div>
          <p class="panel-card__eyebrow">退款核销与资金驳回首批</p>
          <h3>退款待审核 / 退款驳回 / 单据核销</h3>
          <p>首批支持退款审核流转与单笔核销，不开放批量退款、批量核销与自动补偿重放。</p>
        </div>
        <div class="funds-reconcile-filter-actions">
          <ElSelect v-model="docType" class="funds-reconcile-filter-select" @change="reloadDocs">
            <ElOption v-for="item in docTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="statusFilter" class="funds-reconcile-filter-select" clearable placeholder="全部单据状态" @change="reloadDocs">
            <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="refundStatusFilter" class="funds-reconcile-filter-select" clearable placeholder="全部退款状态" @change="reloadDocs">
            <ElOption v-for="item in refundStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElButton type="primary" :loading="loading" @click="reloadDocs">刷新列表</ElButton>
        </div>
      </div>
    </section>

    <section class="funds-reconcile-main-grid">
      <article class="panel-card funds-reconcile-list-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">资金单据列表</p>
            <h3>{{ currentDocTypeLabel }}共 {{ docList.length }} 条</h3>
          </div>
          <span>按创建时间倒序</span>
        </header>

        <ElTable
          v-loading="loading"
          :data="filteredDocList"
          row-key="id"
          highlight-current-row
          :row-class-name="resolveDocRowClass"
          @current-change="handleCurrentChange"
        >
          <ElTableColumn prop="doc_no" label="单据号" min-width="150" />
          <ElTableColumn prop="contract_id" label="合同ID" min-width="110" />
          <ElTableColumn :label="relatedOrderLabel" min-width="120">
            <template #default="scope">
              {{ resolveRelatedOrderId(scope.row) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="实收/实付金额" min-width="130">
            <template #default="scope">
              ¥{{ formatMoney(scope.row.amount_actual) }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="status" label="单据状态" min-width="110" />
          <ElTableColumn prop="refund_status" label="退款状态" min-width="110" />
          <ElTableColumn label="退款金额" min-width="120">
            <template #default="scope">
              ¥{{ formatMoney(scope.row.refund_amount) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="确认时间" min-width="160">
            <template #default="scope">
              {{ formatDateTime(scope.row.confirmed_at) }}
            </template>
          </ElTableColumn>
        </ElTable>
      </article>

      <article class="panel-card funds-reconcile-detail-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">单据详情</p>
            <h3>{{ selectedDoc?.doc_no || '未选择单据' }}</h3>
          </div>
          <span v-if="selectedDoc">{{ selectedDoc.status }}</span>
        </header>

        <ElEmpty v-if="!selectedDoc" description="请选择一条资金单据查看详情" />

        <template v-else>
          <div class="funds-reconcile-detail-grid">
            <div class="detail-row">
              <span>单据类型</span>
              <strong>{{ selectedDoc.doc_type }}</strong>
            </div>
            <div class="detail-row">
              <span>退款状态</span>
              <strong>{{ selectedDoc.refund_status }}</strong>
            </div>
            <div class="detail-row">
              <span>退款金额</span>
              <strong>¥{{ formatMoney(selectedDoc.refund_amount) }}</strong>
            </div>
            <div class="detail-row">
              <span>单据状态</span>
              <strong>{{ selectedDoc.status }}</strong>
            </div>
            <div class="detail-row">
              <span>{{ relatedOrderLabel }}</span>
              <strong>{{ resolveRelatedOrderId(selectedDoc) }}</strong>
            </div>
          </div>

          <div class="funds-reconcile-action-row">
            <ElButton type="warning" :disabled="!canRequestRefund" @click="openRefundRequestDialog">发起退款审核</ElButton>
            <ElButton type="success" :disabled="!canReviewRefund" @click="openRefundDecisionDialog('approve')">退款审核通过</ElButton>
            <ElButton type="danger" :disabled="!canReviewRefund" @click="openRefundDecisionDialog('reject')">退款驳回</ElButton>
            <ElButton type="primary" :disabled="!canWriteoff" @click="openWriteoffDialog">执行核销</ElButton>
          </div>
          <p class="order-boundary-tip">首批仅开放单笔退款审核与单笔核销，不开放批量处理与自动补偿任务。</p>
        </template>
      </article>
    </section>

    <ElDialog v-model="refundRequestDialog.visible" width="560" title="发起退款审核">
      <ElForm label-position="top">
        <ElFormItem label="退款金额">
          <ElInputNumber
            v-model="refundRequestDialog.refundAmount"
            :min="0.01"
            :precision="2"
            :step="100"
            class="order-input-number"
          />
        </ElFormItem>
        <ElFormItem label="退款申请说明">
          <ElInput
            v-model="refundRequestDialog.reason"
            type="textarea"
            maxlength="256"
            show-word-limit
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文退款申请说明"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="refundRequestDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="refundRequestDialog.submitting" @click="submitRefundRequest">确认提交</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="refundDecisionDialog.visible" width="560" :title="refundDecisionDialog.mode === 'approve' ? '退款审核通过' : '退款驳回'">
      <ElForm label-position="top">
        <ElFormItem label="审核说明">
          <ElInput
            v-model="refundDecisionDialog.reason"
            type="textarea"
            maxlength="256"
            show-word-limit
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文审核说明"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="refundDecisionDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="refundDecisionDialog.submitting" @click="submitRefundDecision">确认提交</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="writeoffDialog.visible" width="560" title="执行核销">
      <ElForm label-position="top">
        <ElFormItem label="核销说明">
          <ElInput
            v-model="writeoffDialog.comment"
            type="textarea"
            maxlength="256"
            show-word-limit
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文核销说明"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="writeoffDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="writeoffDialog.submitting" @click="submitWriteoff">确认提交</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script setup lang="ts">
import {
  ElAlert,
  ElButton,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElMessage,
} from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import {
  approvePaymentRefund,
  approveReceiptRefund,
  fetchPaymentDocDetail,
  fetchPaymentDocs,
  fetchReceiptDocDetail,
  fetchReceiptDocs,
  rejectPaymentRefund,
  rejectReceiptRefund,
  requestPaymentRefund,
  requestReceiptRefund,
  writeoffPaymentDoc,
  writeoffReceiptDoc,
  type PaymentDocDetailResponse,
  type PaymentDocListItem,
  type ReceiptDocDetailResponse,
  type ReceiptDocListItem,
} from '@/api/funds'
import { formatDateTime, formatMoney } from '@/utils/formatters'

type FundDocType = 'payment' | 'receipt'
type FundDocListItem = PaymentDocListItem | ReceiptDocListItem
type FundDocDetail = PaymentDocDetailResponse | ReceiptDocDetailResponse

const docTypeOptions: Array<{ label: string; value: FundDocType }> = [
  { label: '付款单', value: 'payment' },
  { label: '收款单', value: 'receipt' },
]
const statusOptions = [
  { label: '草稿', value: '草稿' },
  { label: '待补录金额', value: '待补录金额' },
  { label: '已确认', value: '已确认' },
  { label: '已核销', value: '已核销' },
  { label: '已终止', value: '已终止' },
]
const refundStatusOptions = [
  { label: '未退款', value: '未退款' },
  { label: '待审核', value: '待审核' },
  { label: '驳回', value: '驳回' },
  { label: '部分退款', value: '部分退款' },
  { label: '已退款', value: '已退款' },
]

const loading = ref(false)
const errorMessage = ref('')
const docType = ref<FundDocType>('payment')
const statusFilter = ref('')
const refundStatusFilter = ref('')
const docList = ref<FundDocListItem[]>([])
const selectedDocId = ref<number | null>(null)
const selectedDoc = ref<FundDocDetail | null>(null)

const refundRequestDialog = reactive({
  visible: false,
  refundAmount: 0,
  reason: '',
  submitting: false,
})

const refundDecisionDialog = reactive({
  visible: false,
  mode: 'approve' as 'approve' | 'reject',
  reason: '',
  submitting: false,
})

const writeoffDialog = reactive({
  visible: false,
  comment: '',
  submitting: false,
})

const currentDocTypeLabel = computed(() => (docType.value === 'payment' ? '付款单' : '收款单'))
const relatedOrderLabel = computed(() => (docType.value === 'payment' ? '采购订单ID' : '销售订单ID'))
const canRequestRefund = computed(() =>
  selectedDoc.value ? ['已确认', '已核销'].includes(selectedDoc.value.status) : false,
)
const canReviewRefund = computed(() => selectedDoc.value?.refund_status === '待审核')
const canWriteoff = computed(() => selectedDoc.value?.status === '已确认')
const filteredDocList = computed(() =>
  docList.value.filter((item) => !refundStatusFilter.value || item.refund_status === refundStatusFilter.value),
)

function resolveDocRowClass(params: { row: FundDocListItem }) {
  return params.row.id === selectedDocId.value ? 'is-selected-order-row' : ''
}

function resolveRelatedOrderId(item: FundDocListItem | FundDocDetail): number | string {
  if (docType.value === 'payment') {
    const paymentItem = item as PaymentDocListItem
    return paymentItem.purchase_order_id || '未绑定'
  }
  const receiptItem = item as ReceiptDocListItem
  return receiptItem.sales_order_id || '未绑定'
}

async function loadDocs(preferredId?: number) {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = docType.value === 'payment'
      ? await fetchPaymentDocs(statusFilter.value || undefined)
      : await fetchReceiptDocs(statusFilter.value || undefined)
    docList.value = response.items
    const selectedSource = filteredDocList.value
    if (!selectedSource.length) {
      selectedDocId.value = null
      selectedDoc.value = null
      return
    }
    const nextId = preferredId && selectedSource.some((item) => item.id === preferredId)
      ? preferredId
      : selectedDocId.value && selectedSource.some((item) => item.id === selectedDocId.value)
        ? selectedDocId.value
        : selectedSource[0].id
    selectedDocId.value = nextId
    await loadDetail(nextId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '资金单据列表加载失败'
  } finally {
    loading.value = false
  }
}

async function reloadDocs() {
  await loadDocs()
}

async function loadDetail(docId: number) {
  try {
    selectedDoc.value = docType.value === 'payment'
      ? await fetchPaymentDocDetail(docId)
      : await fetchReceiptDocDetail(docId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '资金单据详情加载失败'
    selectedDoc.value = null
  }
}

async function handleCurrentChange(row: FundDocListItem | null) {
  if (!row) {
    return
  }
  selectedDocId.value = row.id
  await loadDetail(row.id)
}

function openRefundRequestDialog() {
  if (!selectedDoc.value || !canRequestRefund.value) {
    ElMessage.warning('当前单据状态不允许发起退款审核')
    return
  }
  refundRequestDialog.visible = true
  refundRequestDialog.refundAmount = Number(selectedDoc.value.amount_actual)
  refundRequestDialog.reason = ''
}

function openRefundDecisionDialog(mode: 'approve' | 'reject') {
  if (!selectedDoc.value || !canReviewRefund.value) {
    ElMessage.warning('当前单据退款状态不允许审核处理')
    return
  }
  refundDecisionDialog.visible = true
  refundDecisionDialog.mode = mode
  refundDecisionDialog.reason = ''
}

function openWriteoffDialog() {
  if (!selectedDoc.value || !canWriteoff.value) {
    ElMessage.warning('当前单据状态不允许核销')
    return
  }
  writeoffDialog.visible = true
  writeoffDialog.comment = ''
}

async function submitRefundRequest() {
  if (!selectedDoc.value) {
    return
  }
  if (refundRequestDialog.refundAmount <= 0) {
    ElMessage.warning('退款金额必须大于0')
    return
  }
  const reason = refundRequestDialog.reason.trim()
  if (!reason) {
    ElMessage.warning('退款申请说明不能为空')
    return
  }
  refundRequestDialog.submitting = true
  try {
    const updated = docType.value === 'payment'
      ? await requestPaymentRefund(selectedDoc.value.id, {
        refund_amount: refundRequestDialog.refundAmount,
        reason,
      })
      : await requestReceiptRefund(selectedDoc.value.id, {
        refund_amount: refundRequestDialog.refundAmount,
        reason,
      })
    ElMessage.success(updated.message || '退款审核申请成功')
    refundRequestDialog.visible = false
    await loadDocs(updated.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '退款审核申请失败')
  } finally {
    refundRequestDialog.submitting = false
  }
}

async function submitRefundDecision() {
  if (!selectedDoc.value) {
    return
  }
  const reason = refundDecisionDialog.reason.trim()
  if (!reason) {
    ElMessage.warning('审核说明不能为空')
    return
  }
  refundDecisionDialog.submitting = true
  try {
    const updated = docType.value === 'payment'
      ? refundDecisionDialog.mode === 'approve'
        ? await approvePaymentRefund(selectedDoc.value.id, { reason })
        : await rejectPaymentRefund(selectedDoc.value.id, { reason })
      : refundDecisionDialog.mode === 'approve'
        ? await approveReceiptRefund(selectedDoc.value.id, { reason })
        : await rejectReceiptRefund(selectedDoc.value.id, { reason })
    ElMessage.success(updated.message || '退款审核处理成功')
    refundDecisionDialog.visible = false
    await loadDocs(updated.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '退款审核处理失败')
  } finally {
    refundDecisionDialog.submitting = false
  }
}

async function submitWriteoff() {
  if (!selectedDoc.value) {
    return
  }
  const comment = writeoffDialog.comment.trim()
  if (!comment) {
    ElMessage.warning('核销说明不能为空')
    return
  }
  writeoffDialog.submitting = true
  try {
    const updated = docType.value === 'payment'
      ? await writeoffPaymentDoc(selectedDoc.value.id, { comment })
      : await writeoffReceiptDoc(selectedDoc.value.id, { comment })
    ElMessage.success(updated.message || '单据核销成功')
    writeoffDialog.visible = false
    await loadDocs(updated.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '单据核销失败')
  } finally {
    writeoffDialog.submitting = false
  }
}

onMounted(async () => {
  await loadDocs()
})
</script>
