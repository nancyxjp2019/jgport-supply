<template>
  <div class="page-stack order-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <section class="panel-card order-filter-card">
      <div class="order-filter-row">
        <div>
          <p class="panel-card__eyebrow">运营订单处理台首批</p>
          <h3>销售订单审批处理</h3>
          <p>首批支持订单列表、详情回看、运营审批与财务审批，不包含退款核销与批量审核。</p>
        </div>
        <div class="order-filter-actions">
          <ElSelect v-model="statusFilter" class="order-filter-select" placeholder="全部状态" clearable>
            <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElButton type="primary" :loading="loading" @click="loadOrders">刷新列表</ElButton>
        </div>
      </div>
    </section>

    <section class="order-main-grid">
      <article class="panel-card order-list-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">订单列表</p>
            <h3>共 {{ orderList.length }} 条</h3>
          </div>
          <span>按创建时间倒序</span>
        </header>

        <ElTable
          v-loading="loading"
          :data="orderList"
          row-key="id"
          highlight-current-row
          :row-class-name="resolveOrderRowClass"
          @current-change="handleCurrentChange"
        >
          <ElTableColumn prop="order_no" label="订单号" min-width="150" />
          <ElTableColumn prop="sales_contract_no" label="销售合同" min-width="140" />
          <ElTableColumn prop="oil_product_id" label="油品" min-width="110" />
          <ElTableColumn label="数量" min-width="120">
            <template #default="scope">
              {{ formatQty(scope.row.qty_ordered) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="单价" min-width="120">
            <template #default="scope">
              ¥{{ formatMoney(scope.row.unit_price) }}
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

      <article class="panel-card order-detail-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">订单详情</p>
            <h3>{{ selectedOrder?.order_no || '未选择订单' }}</h3>
          </div>
          <span v-if="selectedOrder">{{ selectedOrder.status }}</span>
        </header>

        <ElEmpty v-if="!selectedOrder" description="请选择一条销售订单查看详情" />

        <template v-else>
          <div class="order-detail-grid">
            <div class="detail-row">
              <span>销售合同</span>
              <strong>{{ selectedOrder.sales_contract_no }}</strong>
            </div>
            <div class="detail-row">
              <span>油品</span>
              <strong>{{ selectedOrder.oil_product_id }}</strong>
            </div>
            <div class="detail-row">
              <span>数量</span>
              <strong>{{ formatQty(selectedOrder.qty_ordered) }}</strong>
            </div>
            <div class="detail-row">
              <span>单价</span>
              <strong>¥{{ formatMoney(selectedOrder.unit_price) }}</strong>
            </div>
            <div class="detail-row">
              <span>提交说明</span>
              <strong>{{ selectedOrder.submit_comment || '暂无' }}</strong>
            </div>
            <div class="detail-row">
              <span>运营意见</span>
              <strong>{{ selectedOrder.ops_comment || '暂无' }}</strong>
            </div>
            <div class="detail-row">
              <span>财务意见</span>
              <strong>{{ selectedOrder.finance_comment || '暂无' }}</strong>
            </div>
            <div class="detail-row">
              <span>采购订单</span>
              <strong>{{ selectedOrder.purchase_order_id || '未生成' }}</strong>
            </div>
          </div>

          <div class="order-action-row">
            <ElButton type="warning" :disabled="!canOpsDecision || selectedOrder.status !== '待运营审批'" @click="openOpsDialog(true)">
              运营通过
            </ElButton>
            <ElButton :disabled="!canOpsDecision || selectedOrder.status !== '待运营审批'" @click="openOpsDialog(false)">
              运营驳回
            </ElButton>
            <ElButton type="success" :disabled="!canFinanceDecision || selectedOrder.status !== '待财务审批'" @click="openFinanceDialog(true)">
              财务通过
            </ElButton>
            <ElButton type="danger" :disabled="!canFinanceDecision || selectedOrder.status !== '待财务审批'" @click="openFinanceDialog(false)">
              财务驳回
            </ElButton>
          </div>

          <p v-if="!canOpsDecision && !canFinanceDecision" class="order-boundary-tip">当前角色仅可回看订单，暂无审批按钮权限。</p>
          <p class="order-boundary-tip">首批仅开放单笔审批处理，不开放批量审核、退款核销与异常关闭。</p>
        </template>
      </article>
    </section>

    <ElDialog v-model="opsDialog.visible" width="520" :title="opsDialog.result ? '运营审批通过' : '运营审批驳回'">
      <ElForm label-position="top">
        <ElFormItem label="运营审批意见">
          <ElInput
            v-model="opsDialog.comment"
            maxlength="256"
            show-word-limit
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文运营审批意见"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="opsDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :disabled="!canOpsDecision" :loading="opsDialog.submitting" @click="submitOpsApproval">确认提交</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="financeDialog.visible" width="560" :title="financeDialog.result ? '财务审批通过' : '财务审批驳回'">
      <ElForm label-position="top">
        <ElFormItem v-if="financeDialog.result" label="采购合同ID">
          <ElInputNumber v-model="financeDialog.purchaseContractId" :min="1" :step="1" class="order-input-number" />
        </ElFormItem>
        <ElFormItem v-if="financeDialog.result" label="实收金额">
          <ElInputNumber
            v-model="financeDialog.actualReceiptAmount"
            :min="0"
            :precision="2"
            :step="100"
            class="order-input-number"
          />
        </ElFormItem>
        <ElFormItem v-if="financeDialog.result" label="实付金额">
          <ElInputNumber
            v-model="financeDialog.actualPayAmount"
            :min="0"
            :precision="2"
            :step="100"
            class="order-input-number"
          />
        </ElFormItem>
        <ElFormItem label="财务审批意见">
          <ElInput
            v-model="financeDialog.comment"
            maxlength="256"
            show-word-limit
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文财务审批意见"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="financeDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :disabled="!canFinanceDecision" :loading="financeDialog.submitting" @click="submitFinanceApproval">确认提交</ElButton>
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
  approveSalesOrderByFinance,
  approveSalesOrderByOps,
  fetchSalesOrderDetail,
  fetchSalesOrders,
  type SalesOrderDetailResponse,
  type SalesOrderListItem,
} from '@/api/orders'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, formatMoney, formatQty } from '@/utils/formatters'
import { canRoleExecuteAction } from '@/utils/permissions'

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '草稿', value: '草稿' },
  { label: '待运营审批', value: '待运营审批' },
  { label: '待财务审批', value: '待财务审批' },
  { label: '驳回', value: '驳回' },
  { label: '已衍生采购订单', value: '已衍生采购订单' },
]

const loading = ref(false)
const errorMessage = ref('')
const statusFilter = ref('')
const orderList = ref<SalesOrderListItem[]>([])
const selectedOrderId = ref<number | null>(null)
const selectedOrder = ref<SalesOrderDetailResponse | null>(null)

const opsDialog = reactive({
  visible: false,
  result: true,
  comment: '',
  submitting: false,
})

const financeDialog = reactive({
  visible: false,
  result: true,
  purchaseContractId: 0,
  actualReceiptAmount: 0,
  actualPayAmount: 0,
  comment: '',
  submitting: false,
})

const authStore = useAuthStore()
const currentRoleCode = computed(() => authStore.session?.roleCode ?? '')
const canOpsDecision = computed(() => canRoleExecuteAction(currentRoleCode.value, 'orders.ops.approve'))
const canFinanceDecision = computed(() => canRoleExecuteAction(currentRoleCode.value, 'orders.finance.approve'))

function resolveOrderRowClass(params: { row: SalesOrderListItem }) {
  return params.row.id === selectedOrderId.value ? 'is-selected-order-row' : ''
}

async function loadOrders() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchSalesOrders(statusFilter.value || undefined)
    orderList.value = response.items
    if (!orderList.value.length) {
      selectedOrderId.value = null
      selectedOrder.value = null
      return
    }
    const nextId = selectedOrderId.value && orderList.value.some((item) => item.id === selectedOrderId.value)
      ? selectedOrderId.value
      : orderList.value[0].id
    selectedOrderId.value = nextId
    await loadOrderDetail(nextId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '订单列表加载失败'
  } finally {
    loading.value = false
  }
}

async function loadOrderDetail(orderId: number) {
  try {
    selectedOrder.value = await fetchSalesOrderDetail(orderId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '订单详情加载失败'
    selectedOrder.value = null
  }
}

async function handleCurrentChange(row: SalesOrderListItem | null) {
  if (!row) {
    return
  }
  selectedOrderId.value = row.id
  await loadOrderDetail(row.id)
}

function openOpsDialog(result: boolean) {
  if (!selectedOrder.value) {
    return
  }
  if (!canOpsDecision.value) {
    ElMessage.warning('当前角色无权执行运营审批动作')
    return
  }
  opsDialog.visible = true
  opsDialog.result = result
  opsDialog.comment = ''
}

function openFinanceDialog(result: boolean) {
  if (!selectedOrder.value) {
    return
  }
  if (!canFinanceDecision.value) {
    ElMessage.warning('当前角色无权执行财务审批动作')
    return
  }
  financeDialog.visible = true
  financeDialog.result = result
  financeDialog.purchaseContractId = 0
  financeDialog.actualReceiptAmount = 0
  financeDialog.actualPayAmount = 0
  financeDialog.comment = ''
}

async function submitOpsApproval() {
  if (!selectedOrder.value) {
    return
  }
  if (!canOpsDecision.value) {
    ElMessage.warning('当前角色无权执行运营审批动作')
    return
  }
  const comment = opsDialog.comment.trim()
  if (!comment) {
    ElMessage.warning('运营审批意见不能为空')
    return
  }
  opsDialog.submitting = true
  try {
    const updated = await approveSalesOrderByOps(selectedOrder.value.id, {
      result: opsDialog.result,
      comment,
    })
    ElMessage.success(updated.message || '运营审批已提交')
    opsDialog.visible = false
    await loadOrders()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '运营审批提交失败')
  } finally {
    opsDialog.submitting = false
  }
}

async function submitFinanceApproval() {
  if (!selectedOrder.value) {
    return
  }
  if (!canFinanceDecision.value) {
    ElMessage.warning('当前角色无权执行财务审批动作')
    return
  }
  const comment = financeDialog.comment.trim()
  if (!comment) {
    ElMessage.warning('财务审批意见不能为空')
    return
  }
  if (financeDialog.result) {
    if (!financeDialog.purchaseContractId) {
      ElMessage.warning('财务审批通过时必须填写采购合同ID')
      return
    }
  }
  financeDialog.submitting = true
  try {
    const updated = await approveSalesOrderByFinance(selectedOrder.value.id, {
      result: financeDialog.result,
      purchase_contract_id: financeDialog.result ? financeDialog.purchaseContractId : undefined,
      actual_receipt_amount: financeDialog.result ? financeDialog.actualReceiptAmount : undefined,
      actual_pay_amount: financeDialog.result ? financeDialog.actualPayAmount : undefined,
      comment,
    })
    ElMessage.success(updated.message || '财务审批已提交')
    financeDialog.visible = false
    await loadOrders()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '财务审批提交失败')
  } finally {
    financeDialog.submitting = false
  }
}

onMounted(async () => {
  await loadOrders()
})
</script>
