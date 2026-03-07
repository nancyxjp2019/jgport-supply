<template>
  <div class="page-stack funds-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <section class="panel-card funds-filter-card">
      <div class="funds-filter-row">
        <div>
          <p class="panel-card__eyebrow">财务资金处理台首批</p>
          <h3>收款单 / 付款单处理</h3>
          <p>首批支持列表筛选、详情回看、手工补录、单笔确认与凭证路径回看。</p>
        </div>
        <div class="funds-filter-actions">
          <ElSelect v-model="docType" class="funds-filter-select" @change="reloadDocs">
            <ElOption v-for="item in docTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="statusFilter" class="funds-filter-select" placeholder="全部状态" clearable @change="reloadDocs">
            <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElButton type="primary" :loading="loading" @click="reloadDocs">刷新列表</ElButton>
        </div>
      </div>
    </section>

    <section class="funds-main-grid">
      <article class="panel-card funds-list-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">单据列表</p>
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
          <ElTableColumn prop="doc_no" label="单据号" min-width="150" />
          <ElTableColumn prop="contract_id" label="合同ID" min-width="120" />
          <ElTableColumn :label="relatedOrderLabel" min-width="130">
            <template #default="scope">
              {{ resolveRelatedOrderId(scope.row) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="金额" min-width="130">
            <template #default="scope">
              ¥{{ formatMoney(scope.row.amount_actual) }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="status" label="状态" min-width="120" />
          <ElTableColumn label="凭证要求" min-width="120">
            <template #default="scope">
              <ElTag :type="scope.row.voucher_required ? 'danger' : 'info'" round>
                {{ scope.row.voucher_required ? '必传' : '可免传' }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn label="创建时间" min-width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.created_at) }}
            </template>
          </ElTableColumn>
        </ElTable>
      </article>

      <article class="panel-card funds-detail-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">单据详情</p>
            <h3>{{ selectedDoc?.doc_no || '未选择单据' }}</h3>
          </div>
          <span v-if="selectedDoc">{{ selectedDoc.status }}</span>
        </header>

        <ElEmpty v-if="!selectedDoc" description="请选择一条资金单据查看详情" />

        <template v-else>
          <div class="funds-detail-grid">
            <div class="detail-row">
              <span>单据类型</span>
              <strong>{{ selectedDoc.doc_type }}</strong>
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
              <span>实收/实付金额</span>
              <strong>¥{{ formatMoney(selectedDoc.amount_actual) }}</strong>
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
              <span>凭证要求</span>
              <strong>{{ selectedDoc.voucher_required ? '必须上传凭证' : '可免传凭证' }}</strong>
            </div>
            <div class="detail-row">
              <span>免凭证原因</span>
              <strong>{{ selectedDoc.voucher_exempt_reason || '暂无' }}</strong>
            </div>
            <div class="detail-row">
              <span>确认时间</span>
              <strong>{{ formatDateTime(selectedDoc.confirmed_at) }}</strong>
            </div>
          </div>

          <div class="funds-voucher-panel">
            <p class="funds-voucher-title">凭证路径（{{ selectedDoc.voucher_file_paths.length }}）</p>
            <ul v-if="selectedDoc.voucher_file_paths.length" class="funds-voucher-list">
              <li v-for="item in selectedDoc.voucher_file_paths" :key="item">{{ item }}</li>
            </ul>
            <ElEmpty v-else description="当前无凭证路径" />
          </div>

          <div class="funds-action-row">
            <ElButton type="warning" :disabled="!canOperateFunds" @click="openSupplementDialog">手工补录{{ currentDocTypeLabel }}</ElButton>
            <ElButton type="success" :disabled="!canOperateFunds || !isConfirmable" @click="openConfirmDialog">确认当前单据</ElButton>
          </div>
          <p v-if="!canOperateFunds" class="order-boundary-tip">当前角色仅可回看资金单据，暂无补录与确认按钮权限。</p>
          <p class="order-boundary-tip">首批仅开放单笔处理，不开放退款核销、驳回待审核独立处理台与批量操作。</p>
        </template>
      </article>
    </section>

    <ElDialog v-model="supplementDialog.visible" width="560" :title="`手工补录${currentDocTypeLabel}`">
      <ElForm label-position="top">
        <ElFormItem label="合同ID">
          <ElInputNumber v-model="supplementDialog.contractId" :min="1" :step="1" class="order-input-number" />
        </ElFormItem>
        <ElFormItem :label="relatedOrderLabel">
          <ElInputNumber v-model="supplementDialog.relatedOrderId" :min="1" :step="1" class="order-input-number" />
        </ElFormItem>
        <ElFormItem :label="`补录${currentDocTypeLabel}金额`">
          <ElInputNumber
            v-model="supplementDialog.amountActual"
            :min="0.01"
            :precision="2"
            :step="100"
            class="order-input-number"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="supplementDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :disabled="!canOperateFunds" :loading="supplementDialog.submitting" @click="submitSupplement">确认补录</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="confirmDialog.visible" width="600" title="确认资金单据">
      <ElForm label-position="top">
        <ElFormItem :label="`本次确认${currentDocTypeLabel}金额`">
          <ElInputNumber
            v-model="confirmDialog.amountActual"
            :min="0"
            :precision="2"
            :step="100"
            class="order-input-number"
          />
        </ElFormItem>
        <ElFormItem label="凭证路径（每行一条）">
          <ElInput
            v-model="confirmDialog.voucherLines"
            maxlength="1000"
            show-word-limit
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 8 }"
            placeholder="例如：CODEX-TEST-/funds/voucher-001.jpg"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="confirmDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :disabled="!canOperateFunds" :loading="confirmDialog.submitting" @click="submitConfirm">确认提交</ElButton>
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
  ElTag,
  ElMessage,
} from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import {
  confirmPaymentDoc,
  confirmReceiptDoc,
  createPaymentSupplement,
  createReceiptSupplement,
  fetchPaymentDocDetail,
  fetchPaymentDocs,
  fetchReceiptDocDetail,
  fetchReceiptDocs,
  type PaymentDocDetailResponse,
  type PaymentDocListItem,
  type ReceiptDocDetailResponse,
  type ReceiptDocListItem,
} from '@/api/funds'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, formatMoney } from '@/utils/formatters'
import { canRoleExecuteAction } from '@/utils/permissions'

type FundDocType = 'payment' | 'receipt'
type FundDocListItem = PaymentDocListItem | ReceiptDocListItem
type FundDocDetail = PaymentDocDetailResponse | ReceiptDocDetailResponse

const docTypeOptions: Array<{ label: string; value: FundDocType }> = [
  { label: '付款单', value: 'payment' },
  { label: '收款单', value: 'receipt' },
]
const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '草稿', value: '草稿' },
  { label: '待补录金额', value: '待补录金额' },
  { label: '已确认', value: '已确认' },
  { label: '已核销', value: '已核销' },
  { label: '已终止', value: '已终止' },
]

const loading = ref(false)
const errorMessage = ref('')
const docType = ref<FundDocType>('payment')
const statusFilter = ref('')
const docList = ref<FundDocListItem[]>([])
const selectedDocId = ref<number | null>(null)
const selectedDoc = ref<FundDocDetail | null>(null)

const supplementDialog = reactive({
  visible: false,
  contractId: 0,
  relatedOrderId: 0,
  amountActual: 0,
  submitting: false,
})

const confirmDialog = reactive({
  visible: false,
  amountActual: 0,
  voucherLines: '',
  submitting: false,
})

const currentDocTypeLabel = computed(() => (docType.value === 'payment' ? '付款单' : '收款单'))
const relatedOrderLabel = computed(() => (docType.value === 'payment' ? '采购订单ID' : '销售订单ID'))
const isConfirmable = computed(() =>
  selectedDoc.value ? ['草稿', '待补录金额'].includes(selectedDoc.value.status) : false,
)
const authStore = useAuthStore()
const currentRoleCode = computed(() => authStore.session?.roleCode ?? '')
const canOperateFunds = computed(() => canRoleExecuteAction(currentRoleCode.value, 'funds.operate'))

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

function openSupplementDialog() {
  if (!canOperateFunds.value) {
    ElMessage.warning('当前角色无权执行资金补录动作')
    return
  }
  supplementDialog.visible = true
  supplementDialog.contractId = 0
  supplementDialog.relatedOrderId = 0
  supplementDialog.amountActual = 0
}

function openConfirmDialog() {
  if (!selectedDoc.value) {
    return
  }
  if (!canOperateFunds.value) {
    ElMessage.warning('当前角色无权执行资金确认动作')
    return
  }
  if (!isConfirmable.value) {
    ElMessage.warning('当前单据状态不允许确认')
    return
  }
  confirmDialog.visible = true
  confirmDialog.amountActual = Number(selectedDoc.value.amount_actual)
  confirmDialog.voucherLines = selectedDoc.value.voucher_file_paths.join('\n')
}

function normalizeVoucherLines(input: string): string[] {
  return input
    .split(/[,\n]/g)
    .map((item) => item.trim())
    .filter((item, index, all) => item.length > 0 && all.indexOf(item) === index)
}

async function submitSupplement() {
  if (!canOperateFunds.value) {
    ElMessage.warning('当前角色无权执行资金补录动作')
    return
  }
  if (supplementDialog.contractId <= 0 || supplementDialog.relatedOrderId <= 0) {
    ElMessage.warning('合同ID与关联订单ID必须大于0')
    return
  }
  if (supplementDialog.amountActual <= 0) {
    ElMessage.warning('补录金额必须大于0')
    return
  }
  supplementDialog.submitting = true
  try {
    const updated = docType.value === 'payment'
      ? await createPaymentSupplement({
        contract_id: supplementDialog.contractId,
        purchase_order_id: supplementDialog.relatedOrderId,
        amount_actual: supplementDialog.amountActual,
      })
      : await createReceiptSupplement({
        contract_id: supplementDialog.contractId,
        sales_order_id: supplementDialog.relatedOrderId,
        amount_actual: supplementDialog.amountActual,
      })
    ElMessage.success(updated.message || '单据补录成功')
    supplementDialog.visible = false
    await loadDocs(updated.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '单据补录失败')
  } finally {
    supplementDialog.submitting = false
  }
}

async function submitConfirm() {
  if (!selectedDoc.value) {
    return
  }
  if (!canOperateFunds.value) {
    ElMessage.warning('当前角色无权执行资金确认动作')
    return
  }
  const voucherFiles = normalizeVoucherLines(confirmDialog.voucherLines)
  if (confirmDialog.amountActual > 0 && voucherFiles.length === 0) {
    ElMessage.warning('非0金额确认必须至少填写一条凭证路径')
    return
  }
  confirmDialog.submitting = true
  try {
    const updated = docType.value === 'payment'
      ? await confirmPaymentDoc(selectedDoc.value.id, {
        amount_actual: confirmDialog.amountActual,
        voucher_files: voucherFiles,
      })
      : await confirmReceiptDoc(selectedDoc.value.id, {
        amount_actual: confirmDialog.amountActual,
        voucher_files: voucherFiles,
      })
    ElMessage.success(updated.message || '单据确认成功')
    confirmDialog.visible = false
    await loadDocs(updated.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '单据确认失败')
  } finally {
    confirmDialog.submitting = false
  }
}

onMounted(async () => {
  await loadDocs()
})
</script>
