<template>
  <div class="page-stack contract-close-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <section class="panel-card contract-close-filter-card">
      <div class="contract-close-filter-row">
        <div>
          <p class="panel-card__eyebrow">合同关闭差异台首批</p>
          <h3>自动关闭回看 / 手工关闭处置</h3>
          <p>首批支持合同关闭结果回看、差异展示与单笔手工关闭，不开放批量关闭与退款核销联动。</p>
        </div>
        <div class="contract-close-filter-actions">
          <ElSelect v-model="directionFilter" class="contract-close-filter-select" clearable placeholder="全部方向" @change="reloadContracts">
            <ElOption v-for="item in directionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="statusFilter" class="contract-close-filter-select" clearable placeholder="全部状态" @change="reloadContracts">
            <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="closeTypeFilter" class="contract-close-filter-select" clearable placeholder="全部关闭类型" @change="reloadContracts">
            <ElOption v-for="item in closeTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElButton type="primary" :loading="loading" @click="reloadContracts">刷新列表</ElButton>
        </div>
      </div>
    </section>

    <section class="contract-close-main-grid">
      <article class="panel-card contract-close-list-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">合同列表</p>
            <h3>共 {{ contractList.length }} 条</h3>
          </div>
          <span>按创建时间倒序</span>
        </header>

        <ElTable
          v-loading="loading"
          :data="contractList"
          row-key="id"
          highlight-current-row
          :row-class-name="resolveContractRowClass"
          @current-change="handleCurrentChange"
        >
          <ElTableColumn prop="contract_no" label="合同编号" min-width="160" />
          <ElTableColumn label="合同方向" min-width="120">
            <template #default="scope">
              {{ resolveDirectionLabel(scope.row.direction) }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="status" label="状态" min-width="120" />
          <ElTableColumn label="关闭类型" min-width="120">
            <template #default="scope">
              <ElTag :type="resolveCloseTypeTag(scope.row.close_type)" round>
                {{ resolveCloseTypeLabel(scope.row.close_type) }}
              </ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn label="关闭差异金额" min-width="150">
            <template #default="scope">
              {{ resolveDiffAmount(scope.row.manual_close_diff_amount) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="关闭时间" min-width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.closed_at) }}
            </template>
          </ElTableColumn>
        </ElTable>
      </article>

      <article class="panel-card contract-close-detail-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">关闭详情</p>
            <h3>{{ selectedContract?.contract_no || '未选择合同' }}</h3>
          </div>
          <span v-if="selectedContract">{{ selectedContract.status }}</span>
        </header>

        <ElEmpty v-if="!selectedContract" description="请选择一条合同查看关闭详情" />

        <template v-else>
          <div class="contract-close-detail-grid">
            <div class="detail-row">
              <span>合同方向</span>
              <strong>{{ resolveDirectionLabel(selectedContract.direction) }}</strong>
            </div>
            <div class="detail-row">
              <span>关闭类型</span>
              <strong>{{ resolveCloseTypeLabel(selectedContract.close_type) }}</strong>
            </div>
            <div class="detail-row">
              <span>合同状态</span>
              <strong>{{ selectedContract.status }}</strong>
            </div>
            <div class="detail-row">
              <span>关闭操作者</span>
              <strong>{{ selectedContract.closed_by || '未关闭' }}</strong>
            </div>
            <div class="detail-row">
              <span>关闭时间</span>
              <strong>{{ formatDateTime(selectedContract.closed_at) }}</strong>
            </div>
            <div class="detail-row">
              <span>手工关闭原因</span>
              <strong>{{ selectedContract.manual_close_reason || '暂无' }}</strong>
            </div>
            <div class="detail-row">
              <span>手工差异金额</span>
              <strong>{{ resolveDiffAmount(selectedContract.manual_close_diff_amount) }}</strong>
            </div>
          </div>

          <div
            v-if="manualCloseDiffRows.length"
            class="contract-close-diff-panel"
          >
            <p class="contract-close-diff-title">手工关闭数量差异（{{ manualCloseDiffRows.length }}）</p>
            <ElTable :data="manualCloseDiffRows" size="small">
              <ElTableColumn prop="oil_product_id" label="油品" min-width="100" />
              <ElTableColumn prop="qty_signed" label="签约数量" min-width="100" />
              <ElTableColumn prop="qty_in_acc" label="累计入库" min-width="100" />
              <ElTableColumn prop="qty_out_acc" label="累计出库" min-width="100" />
              <ElTableColumn prop="qty_gap" label="剩余差异" min-width="100" />
            </ElTable>
          </div>

          <div class="contract-close-alert-panel" :class="`is-${detailSeverity}`">
            <p class="contract-close-alert-title">关闭处置提示</p>
            <p>{{ detailHint }}</p>
          </div>

          <div class="contract-close-action-row">
            <ElButton type="warning" :disabled="!canManualClose" @click="openManualCloseDialog">手工关闭当前合同</ElButton>
          </div>
          <p class="order-boundary-tip">首批仅开放单笔手工关闭，不开放批量关闭、退款核销联动与多维报表收口分析。</p>
        </template>
      </article>
    </section>

    <ElDialog v-model="manualCloseDialog.visible" width="620" title="手工关闭合同">
      <ElForm label-position="top">
        <ElFormItem label="合同编号">
          <ElInput :model-value="selectedContract?.contract_no || ''" disabled />
        </ElFormItem>
        <ElFormItem label="手工关闭原因">
          <ElInput
            v-model="manualCloseDialog.reason"
            type="textarea"
            maxlength="256"
            show-word-limit
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文手工关闭原因"
          />
        </ElFormItem>
        <ElFormItem label="确认口令">
          <ElInput v-model="manualCloseDialog.confirmToken" maxlength="32" placeholder="MANUAL_CLOSE" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="manualCloseDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="manualCloseDialog.submitting" @click="submitCurrentContractManualClose">确认关闭</ElButton>
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
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
  ElMessage,
} from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import {
  fetchCloseContractDetail,
  fetchCloseContracts,
  submitManualClose,
  type ContractDetailResponse,
  type ContractListItem,
} from '@/api/contract-close'
import { useAuthStore } from '@/stores/auth'
import { canRoleExecuteAction } from '@/utils/permissions'
import { formatDateTime, formatMoney } from '@/utils/formatters'

type ContractCloseDiffDisplayRow = {
  oil_product_id: string
  qty_signed: string
  qty_in_acc: string
  qty_out_acc: string
  qty_gap: string
}

const directionOptions = [
  { label: '销售合同', value: 'sales' },
  { label: '采购合同', value: 'purchase' },
]
const statusOptions = [
  { label: '草稿', value: '草稿' },
  { label: '待审批', value: '待审批' },
  { label: '生效中', value: '生效中' },
  { label: '数量履约完成', value: '数量履约完成' },
  { label: '已关闭', value: '已关闭' },
  { label: '手工关闭', value: '手工关闭' },
]
const closeTypeOptions = [
  { label: '自动关闭', value: 'AUTO' },
  { label: '手工关闭', value: 'MANUAL' },
]

const loading = ref(false)
const errorMessage = ref('')
const directionFilter = ref('')
const statusFilter = ref('')
const closeTypeFilter = ref('')
const contractList = ref<ContractListItem[]>([])
const selectedContractId = ref<number | null>(null)
const selectedContract = ref<ContractDetailResponse | null>(null)

const manualCloseDialog = reactive({
  visible: false,
  reason: '',
  confirmToken: 'MANUAL_CLOSE',
  submitting: false,
})

const authStore = useAuthStore()
const currentRoleCode = computed(() => authStore.session?.roleCode ?? '')
const canManualCloseWrite = computed(() => canRoleExecuteAction(currentRoleCode.value, 'contracts.write'))
const canManualClose = computed(() => canManualCloseWrite.value && selectedContract.value?.status === '数量履约完成')
const manualCloseDiffRows = computed<ContractCloseDiffDisplayRow[]>(() => {
  if (!selectedContract.value?.manual_close_diff_qty_json?.length) {
    return []
  }
  return selectedContract.value.manual_close_diff_qty_json.map((row) =>
    resolveManualCloseDiffRow(selectedContract.value as ContractDetailResponse, row),
  )
})

const detailSeverity = computed(() => {
  if (!selectedContract.value) {
    return 'neutral'
  }
  if (selectedContract.value.status === '数量履约完成') {
    return 'warning'
  }
  if (selectedContract.value.status === '手工关闭') {
    return 'danger'
  }
  if (selectedContract.value.status === '已关闭') {
    return 'success'
  }
  return 'info'
})

const detailHint = computed(() => {
  if (!selectedContract.value) {
    return '请选择合同后查看关闭处置提示。'
  }
  if (selectedContract.value.status === '数量履约完成') {
    return '当前合同仅完成数量履约，金额链路可能未闭环，可在确认风险后执行手工关闭。'
  }
  if (selectedContract.value.status === '手工关闭') {
    return '当前合同已手工关闭，请重点回看关闭原因、差异金额与油品数量差异留痕。'
  }
  if (selectedContract.value.status === '已关闭') {
    return '当前合同已自动关闭，表示数量与金额链路已完成收口。'
  }
  return '当前合同尚未进入关闭阶段，请先完成前置执行链路。'
})

function resolveContractRowClass(params: { row: ContractListItem }) {
  return params.row.id === selectedContractId.value ? 'is-selected-order-row' : ''
}

function resolveDirectionLabel(direction: string): string {
  if (direction === 'sales' || direction === 'SALES') {
    return '销售合同'
  }
  if (direction === 'purchase' || direction === 'PURCHASE') {
    return '采购合同'
  }
  return direction
}

function resolveCloseTypeLabel(closeType: string | null): string {
  if (closeType === 'AUTO') {
    return '自动关闭'
  }
  if (closeType === 'MANUAL') {
    return '手工关闭'
  }
  return '未关闭'
}

function resolveCloseTypeTag(closeType: string | null): 'success' | 'warning' | 'info' {
  if (closeType === 'AUTO') {
    return 'success'
  }
  if (closeType === 'MANUAL') {
    return 'warning'
  }
  return 'info'
}

function resolveDiffAmount(amount: string | null): string {
  if (!amount) {
    return '--'
  }
  return `¥${formatMoney(amount)}`
}

function resolveManualCloseDiffRow(
  contract: ContractDetailResponse,
  row: Record<string, string>,
): ContractCloseDiffDisplayRow {
  if ('qty_in_acc' in row || 'qty_out_acc' in row || 'qty_gap' in row) {
    return {
      oil_product_id: row.oil_product_id || '--',
      qty_signed: row.qty_signed || '0.000',
      qty_in_acc: row.qty_in_acc || '0.000',
      qty_out_acc: row.qty_out_acc || '0.000',
      qty_gap: row.qty_gap || row.diff_qty || '0.000',
    }
  }

  const normalizedDirection = String(contract.direction || '').toLowerCase()
  const qtyDone = row.qty_done || '0.000'
  return {
    oil_product_id: row.oil_product_id || '--',
    qty_signed: row.qty_signed || '0.000',
    qty_in_acc: normalizedDirection === 'purchase' ? qtyDone : '0.000',
    qty_out_acc: normalizedDirection === 'sales' ? qtyDone : '0.000',
    qty_gap: row.diff_qty || '0.000',
  }
}

async function loadContracts(preferredId?: number) {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchCloseContracts({
      status: statusFilter.value || undefined,
      direction: directionFilter.value || undefined,
      close_type: closeTypeFilter.value || undefined,
    })
    contractList.value = response.items
    if (!contractList.value.length) {
      selectedContractId.value = null
      selectedContract.value = null
      return
    }
    const nextId = preferredId && contractList.value.some((item) => item.id === preferredId)
      ? preferredId
      : selectedContractId.value && contractList.value.some((item) => item.id === selectedContractId.value)
        ? selectedContractId.value
        : contractList.value[0].id
    selectedContractId.value = nextId
    await loadContractDetail(nextId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '合同列表加载失败'
  } finally {
    loading.value = false
  }
}

async function reloadContracts() {
  await loadContracts()
}

async function loadContractDetail(contractId: number) {
  try {
    selectedContract.value = await fetchCloseContractDetail(contractId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '合同详情加载失败'
    selectedContract.value = null
  }
}

async function handleCurrentChange(row: ContractListItem | null) {
  if (!row) {
    return
  }
  selectedContractId.value = row.id
  await loadContractDetail(row.id)
}

function openManualCloseDialog() {
  if (!selectedContract.value) {
    return
  }
  if (!canManualCloseWrite.value) {
    ElMessage.warning('当前角色无权执行手工关闭动作')
    return
  }
  if (!canManualClose.value) {
    ElMessage.warning('当前合同状态不允许手工关闭')
    return
  }
  manualCloseDialog.visible = true
  manualCloseDialog.reason = ''
  manualCloseDialog.confirmToken = 'MANUAL_CLOSE'
}

async function submitCurrentContractManualClose() {
  if (!selectedContract.value) {
    return
  }
  if (!canManualCloseWrite.value) {
    ElMessage.warning('当前角色无权执行手工关闭动作')
    return
  }
  const reason = manualCloseDialog.reason.trim()
  const confirmToken = manualCloseDialog.confirmToken.trim()
  if (!reason) {
    ElMessage.warning('手工关闭原因不能为空')
    return
  }
  if (!confirmToken) {
    ElMessage.warning('确认口令不能为空')
    return
  }
  manualCloseDialog.submitting = true
  try {
    const updated = await submitManualClose(selectedContract.value.id, {
      reason,
      confirm_token: confirmToken,
    })
    ElMessage.success(updated.message || '合同手工关闭成功')
    manualCloseDialog.visible = false
    await loadContracts(updated.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '合同手工关闭失败')
  } finally {
    manualCloseDialog.submitting = false
  }
}

onMounted(async () => {
  await loadContracts()
})
</script>
