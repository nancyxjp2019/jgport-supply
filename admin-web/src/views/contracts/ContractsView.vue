<template>
  <div class="page-stack contracts-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <section class="panel-card contracts-filter-card">
      <div class="contracts-filter-row">
        <div>
          <p class="panel-card__eyebrow">合同管理台首批</p>
          <h3>采购 / 销售合同提审审批</h3>
          <p>首批支持合同列表、详情、草稿编辑、提审、审批与图谱摘要回看，合同关闭继续复用现有差异台。</p>
        </div>
        <div class="contracts-filter-actions">
          <ElSelect v-model="directionFilter" class="contracts-filter-select" clearable placeholder="全部方向" @change="reloadContracts">
            <ElOption v-for="item in directionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="statusFilter" class="contracts-filter-select" clearable placeholder="全部状态" @change="reloadContracts">
            <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElButton type="primary" :loading="loading" @click="reloadContracts">刷新列表</ElButton>
          <ElButton type="success" :disabled="!canWriteContract" @click="openCreateDialog('purchase')">新建采购合同</ElButton>
          <ElButton :disabled="!canWriteContract" @click="openCreateDialog('sales')">新建销售合同</ElButton>
        </div>
      </div>
    </section>

    <section class="contracts-main-grid">
      <article class="panel-card contracts-list-card">
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
          <ElTableColumn prop="contract_no" label="合同编号" min-width="150" />
          <ElTableColumn label="方向" min-width="110">
            <template #default="scope">
              {{ resolveDirectionLabel(scope.row.direction) }}
            </template>
          </ElTableColumn>
          <ElTableColumn label="对方主体" min-width="160">
            <template #default="scope">
              {{ resolveCounterparty(scope.row) }}
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

      <article class="panel-card contracts-detail-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">合同详情</p>
            <h3>{{ selectedContract?.contract_no || '未选择合同' }}</h3>
          </div>
          <span v-if="selectedContract">{{ selectedContract.status }}</span>
        </header>

        <ElEmpty v-if="!selectedContract" description="请选择一条合同查看详情" />

        <template v-else>
          <div class="contracts-detail-grid">
            <div class="detail-row">
              <span>合同方向</span>
              <strong>{{ resolveDirectionLabel(selectedContract.direction) }}</strong>
            </div>
            <div class="detail-row">
              <span>对方主体</span>
              <strong>{{ resolveCounterparty(selectedContract) }}</strong>
            </div>
            <div class="detail-row">
              <span>提交说明</span>
              <strong>{{ selectedContract.submit_comment || '暂无' }}</strong>
            </div>
            <div class="detail-row">
              <span>审批意见</span>
              <strong>{{ selectedContract.approval_comment || '暂无' }}</strong>
            </div>
            <div class="detail-row">
              <span>提审时间</span>
              <strong>{{ formatDateTime(selectedContract.submitted_at) }}</strong>
            </div>
            <div class="detail-row">
              <span>审批时间</span>
              <strong>{{ formatDateTime(selectedContract.approved_at) }}</strong>
            </div>
            <div class="detail-row">
              <span>释放阈值快照</span>
              <strong>{{ selectedContract.threshold_release_snapshot || '--' }}</strong>
            </div>
            <div class="detail-row">
              <span>超发超收阈值快照</span>
              <strong>{{ selectedContract.threshold_over_exec_snapshot || '--' }}</strong>
            </div>
          </div>

          <div class="contracts-subsection">
            <div class="panel-card__header">
              <div>
                <p class="panel-card__eyebrow">油品明细</p>
                <h3>共 {{ selectedContract.items.length }} 项</h3>
              </div>
            </div>
            <ElTable :data="selectedContract.items" size="small">
              <ElTableColumn prop="oil_product_id" label="油品" min-width="100" />
              <ElTableColumn prop="qty_signed" label="签约数量" min-width="100" />
              <ElTableColumn label="单价" min-width="120">
                <template #default="scope">
                  ¥{{ formatMoney(scope.row.unit_price) }}
                </template>
              </ElTableColumn>
              <ElTableColumn prop="qty_in_acc" label="累计入库" min-width="100" />
              <ElTableColumn prop="qty_out_acc" label="累计出库" min-width="100" />
            </ElTable>
          </div>

          <div class="contracts-subsection">
            <div class="panel-card__header">
              <div>
                <p class="panel-card__eyebrow">图谱摘要</p>
                <h3>下游待处理任务 {{ selectedGraph?.downstream_tasks.length || 0 }} 条</h3>
              </div>
            </div>
            <ElTable v-if="selectedGraph?.downstream_tasks.length" :data="selectedGraph.downstream_tasks" size="small">
              <ElTableColumn label="目标单据" min-width="120">
                <template #default="scope">
                  {{ resolveTaskTypeLabel(scope.row.target_doc_type) }}
                </template>
              </ElTableColumn>
              <ElTableColumn prop="status" label="状态" min-width="100" />
              <ElTableColumn prop="idempotency_key" label="幂等键" min-width="180" />
            </ElTable>
            <ElEmpty v-else description="当前合同暂无下游待处理任务" />
          </div>

          <div class="contracts-action-row">
            <ElButton :disabled="!canEditCurrentContract" @click="openEditDialog">编辑草稿</ElButton>
            <ElButton type="warning" :disabled="!canSubmitContract" @click="openSubmitDialog">提交审批</ElButton>
            <ElButton type="success" :disabled="!canApproveCurrentContract" @click="openApprovalDialog(true)">审批通过</ElButton>
            <ElButton type="danger" :disabled="!canApproveCurrentContract" @click="openApprovalDialog(false)">审批驳回</ElButton>
          </div>

          <p v-if="selectedContract.status === '草稿' && selectedContract.approval_comment" class="order-boundary-tip">
            当前合同曾被退回修改，可先编辑草稿后再次提交审批。
          </p>
          <p v-if="!canWriteContract && !canApproveContract" class="order-boundary-tip">当前角色仅可回看合同列表、详情与图谱摘要。</p>
          <p class="order-boundary-tip">合同手工关闭继续在“合同关闭差异台”处理，本页不重复建设关闭动作。</p>
        </template>
      </article>
    </section>

    <ElDialog
      v-model="createDialog.visible"
      width="760"
      :title="resolveEditorDialogTitle()"
    >
      <ElForm label-position="top">
        <ElFormItem label="合同编号">
          <ElInput v-model="createDialog.contractNo" maxlength="64" placeholder="请输入合同编号" />
        </ElFormItem>
        <ElFormItem :label="createDialog.direction === 'purchase' ? '供应商ID' : '客户ID'">
          <ElInput v-model="createDialog.counterpartyId" maxlength="64" :placeholder="createDialog.direction === 'purchase' ? '请输入供应商ID' : '请输入客户ID'" />
        </ElFormItem>
        <div class="contracts-create-items-header">
          <strong>油品明细</strong>
          <ElButton link type="primary" @click="addCreateItem">新增明细</ElButton>
        </div>
        <div v-for="(item, index) in createDialog.items" :key="index" class="contracts-create-item-row">
          <ElFormItem :label="`油品${index + 1}`">
            <ElInput v-model="item.oil_product_id" maxlength="64" placeholder="油品ID，如 OIL-92" />
          </ElFormItem>
          <ElFormItem label="签约数量">
            <ElInputNumber v-model="item.qty_signed" :min="0.001" :step="1" :precision="3" class="contracts-input-number" />
          </ElFormItem>
          <ElFormItem label="合同单价">
            <ElInputNumber v-model="item.unit_price" :min="0.01" :step="100" :precision="2" class="contracts-input-number" />
          </ElFormItem>
          <ElButton text :disabled="createDialog.items.length <= 1" @click="removeCreateItem(index)">删除</ElButton>
        </div>
      </ElForm>
      <template #footer>
        <ElButton @click="createDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :disabled="!canWriteContract" :loading="createDialog.submitting" @click="submitCreate">
          {{ createDialog.mode === 'edit' ? '保存修改' : '确认创建' }}
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="submitDialog.visible" width="560" title="提交合同审批">
      <ElForm label-position="top">
        <ElFormItem label="合同编号">
          <ElInput :model-value="selectedContract?.contract_no || ''" disabled />
        </ElFormItem>
        <ElFormItem label="提交说明">
          <ElInput
            v-model="submitDialog.comment"
            maxlength="256"
            show-word-limit
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文提交说明"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="submitDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :disabled="!canWriteContract" :loading="submitDialog.submitting" @click="submitCurrentContract">确认提交</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="approvalDialog.visible" width="560" :title="approvalDialog.result ? '合同审批通过' : '合同审批驳回'">
      <ElForm label-position="top">
        <ElFormItem label="合同编号">
          <ElInput :model-value="selectedContract?.contract_no || ''" disabled />
        </ElFormItem>
        <ElFormItem label="审批意见">
          <ElInput
            v-model="approvalDialog.comment"
            maxlength="256"
            show-word-limit
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文审批意见"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="approvalDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :disabled="!canApproveContract" :loading="approvalDialog.submitting" @click="submitApproval">确认提交</ElButton>
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
  approveContract,
  createPurchaseContract,
  createSalesContract,
  fetchContractDetail,
  fetchContractGraph,
  fetchContracts,
  submitContract,
  updateContract,
  type ContractDetailResponse,
  type ContractGraphResponse,
  type ContractListItem,
} from '@/api/contracts'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, formatMoney } from '@/utils/formatters'
import { canRoleExecuteAction } from '@/utils/permissions'

const directionOptions = [
  { label: '采购合同', value: 'purchase' },
  { label: '销售合同', value: 'sales' },
]
const statusOptions = [
  { label: '草稿', value: '草稿' },
  { label: '待审批', value: '待审批' },
  { label: '生效中', value: '生效中' },
  { label: '数量履约完成', value: '数量履约完成' },
  { label: '已关闭', value: '已关闭' },
  { label: '手工关闭', value: '手工关闭' },
]

const loading = ref(false)
const errorMessage = ref('')
const directionFilter = ref('')
const statusFilter = ref('')
const contractList = ref<ContractListItem[]>([])
const selectedContractId = ref<number | null>(null)
const selectedContract = ref<ContractDetailResponse | null>(null)
const selectedGraph = ref<ContractGraphResponse | null>(null)

const createDialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  contractId: null as number | null,
  direction: 'purchase' as 'purchase' | 'sales',
  contractNo: '',
  counterpartyId: '',
  items: [{ oil_product_id: '', qty_signed: 1, unit_price: 6000 }],
  submitting: false,
})

const submitDialog = reactive({
  visible: false,
  comment: '',
  submitting: false,
})

const approvalDialog = reactive({
  visible: false,
  result: true,
  comment: '',
  submitting: false,
})

const authStore = useAuthStore()
const currentRoleCode = computed(() => authStore.session?.roleCode ?? '')
const canViewContracts = computed(() => canRoleExecuteAction(currentRoleCode.value, 'contracts.view'))
const canWriteContract = computed(() => canRoleExecuteAction(currentRoleCode.value, 'contracts.write'))
const canApproveContract = computed(() => canRoleExecuteAction(currentRoleCode.value, 'contracts.approve'))
const canEditCurrentContract = computed(() => canWriteContract.value && selectedContract.value?.status === '草稿')
const canSubmitContract = computed(() => canWriteContract.value && selectedContract.value?.status === '草稿')
const canApproveCurrentContract = computed(() => canApproveContract.value && selectedContract.value?.status === '待审批')

function resolveEditorDialogTitle(): string {
  if (createDialog.mode === 'edit') {
    return createDialog.direction === 'purchase' ? '编辑采购合同' : '编辑销售合同'
  }
  return createDialog.direction === 'purchase' ? '新建采购合同' : '新建销售合同'
}

function resolveDirectionLabel(direction: string): string {
  if (direction === 'purchase') {
    return '采购合同'
  }
  if (direction === 'sales') {
    return '销售合同'
  }
  return direction
}

function resolveCounterparty(contract: Pick<ContractListItem, 'direction' | 'supplier_id' | 'customer_id'>): string {
  if (contract.direction === 'purchase') {
    return contract.supplier_id || '--'
  }
  return contract.customer_id || '--'
}

function resolveTaskTypeLabel(taskType: string): string {
  if (taskType === 'payment_doc') {
    return '付款单任务'
  }
  if (taskType === 'receipt_doc') {
    return '收款单任务'
  }
  if (taskType === 'inbound_doc') {
    return '入库单任务'
  }
  if (taskType === 'outbound_doc') {
    return '出库单任务'
  }
  return taskType
}

function resolveContractRowClass(params: { row: ContractListItem }) {
  return params.row.id === selectedContractId.value ? 'is-selected-order-row' : ''
}

async function loadContractPanel(contractId: number) {
  try {
    const [detail, graph] = await Promise.all([
      fetchContractDetail(contractId),
      fetchContractGraph(contractId),
    ])
    selectedContract.value = detail
    selectedGraph.value = graph
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '合同详情加载失败'
    selectedContract.value = null
    selectedGraph.value = null
  }
}

async function loadContracts(preferredId?: number) {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchContracts({
      status: statusFilter.value || undefined,
      direction: directionFilter.value || undefined,
    })
    contractList.value = response.items
    if (!contractList.value.length) {
      selectedContractId.value = null
      selectedContract.value = null
      selectedGraph.value = null
      return
    }
    const nextId = preferredId && contractList.value.some((item) => item.id === preferredId)
      ? preferredId
      : selectedContractId.value && contractList.value.some((item) => item.id === selectedContractId.value)
        ? selectedContractId.value
        : contractList.value[0].id
    selectedContractId.value = nextId
    await loadContractPanel(nextId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '合同列表加载失败'
  } finally {
    loading.value = false
  }
}

async function reloadContracts() {
  await loadContracts()
}

async function handleCurrentChange(row: ContractListItem | null) {
  if (!row) {
    return
  }
  selectedContractId.value = row.id
  await loadContractPanel(row.id)
}

function resetCreateDialog(direction: 'purchase' | 'sales') {
  createDialog.mode = 'create'
  createDialog.contractId = null
  createDialog.direction = direction
  createDialog.contractNo = ''
  createDialog.counterpartyId = ''
  createDialog.items = [{ oil_product_id: '', qty_signed: 1, unit_price: 6000 }]
}

function openCreateDialog(direction: 'purchase' | 'sales') {
  if (!canWriteContract.value) {
    ElMessage.warning('当前角色无权创建合同')
    return
  }
  resetCreateDialog(direction)
  createDialog.visible = true
}

function openEditDialog() {
  if (!selectedContract.value) {
    return
  }
  if (!canWriteContract.value) {
    ElMessage.warning('当前角色无权修改合同')
    return
  }
  if (selectedContract.value.status !== '草稿') {
    ElMessage.warning('仅草稿合同可修改')
    return
  }
  createDialog.mode = 'edit'
  createDialog.contractId = selectedContract.value.id
  createDialog.direction = selectedContract.value.direction === 'purchase' ? 'purchase' : 'sales'
  createDialog.contractNo = selectedContract.value.contract_no
  createDialog.counterpartyId = createDialog.direction === 'purchase'
    ? selectedContract.value.supplier_id || ''
    : selectedContract.value.customer_id || ''
  createDialog.items = selectedContract.value.items.map((item) => ({
    oil_product_id: item.oil_product_id,
    qty_signed: Number(item.qty_signed),
    unit_price: Number(item.unit_price),
  }))
  createDialog.visible = true
}

function addCreateItem() {
  createDialog.items.push({ oil_product_id: '', qty_signed: 1, unit_price: 6000 })
}

function removeCreateItem(index: number) {
  if (createDialog.items.length <= 1) {
    return
  }
  createDialog.items.splice(index, 1)
}

async function submitCreate() {
  if (!canWriteContract.value) {
    ElMessage.warning('当前角色无权维护合同')
    return
  }
  createDialog.submitting = true
  try {
    const payload = {
      contract_no: createDialog.contractNo.trim(),
      items: createDialog.items.map((item) => ({
        oil_product_id: item.oil_product_id.trim(),
        qty_signed: Number(item.qty_signed),
        unit_price: Number(item.unit_price),
      })),
    }
    let result: ContractDetailResponse
    if (createDialog.mode === 'edit') {
      result = await updateContract(createDialog.contractId as number, {
        ...payload,
        supplier_id: createDialog.direction === 'purchase' ? createDialog.counterpartyId.trim() : undefined,
        customer_id: createDialog.direction === 'sales' ? createDialog.counterpartyId.trim() : undefined,
      })
    } else if (createDialog.direction === 'purchase') {
      result = await createPurchaseContract({
        ...payload,
        supplier_id: createDialog.counterpartyId.trim(),
      })
    } else {
      result = await createSalesContract({
        ...payload,
        customer_id: createDialog.counterpartyId.trim(),
      })
    }
    ElMessage.success(result.message || (createDialog.mode === 'edit' ? '合同草稿已更新' : '合同草稿创建成功'))
    createDialog.visible = false
    await loadContracts(result.id)
  } catch (error) {
    ElMessage.error(
      error instanceof Error
        ? error.message
        : createDialog.mode === 'edit'
          ? '合同草稿修改失败'
          : '合同草稿创建失败',
    )
  } finally {
    createDialog.submitting = false
  }
}

function openSubmitDialog() {
  if (!selectedContract.value) {
    return
  }
  if (!canWriteContract.value) {
    ElMessage.warning('当前角色无权提交合同审批')
    return
  }
  if (selectedContract.value.status !== '草稿') {
    ElMessage.warning('仅草稿合同可提交审批')
    return
  }
  submitDialog.visible = true
  submitDialog.comment = ''
}

async function submitCurrentContract() {
  if (!selectedContract.value) {
    return
  }
  if (!canWriteContract.value) {
    ElMessage.warning('当前角色无权提交合同审批')
    return
  }
  if (selectedContract.value.status !== '草稿') {
    ElMessage.warning('仅草稿合同可提交审批')
    return
  }
  const comment = submitDialog.comment.trim()
  if (!comment) {
    ElMessage.warning('提交说明不能为空')
    return
  }
  submitDialog.submitting = true
  try {
    const updated = await submitContract(selectedContract.value.id, { comment })
    ElMessage.success(updated.message || '合同已提交审批')
    submitDialog.visible = false
    await loadContracts(updated.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '合同提交审批失败')
  } finally {
    submitDialog.submitting = false
  }
}

function openApprovalDialog(result: boolean) {
  if (!selectedContract.value) {
    return
  }
  if (!canApproveContract.value) {
    ElMessage.warning('当前角色无权执行合同审批')
    return
  }
  if (selectedContract.value.status !== '待审批') {
    ElMessage.warning('仅待审批合同可执行审批')
    return
  }
  approvalDialog.visible = true
  approvalDialog.result = result
  approvalDialog.comment = ''
}

async function submitApproval() {
  if (!selectedContract.value) {
    return
  }
  if (!canApproveContract.value) {
    ElMessage.warning('当前角色无权执行合同审批')
    return
  }
  if (selectedContract.value.status !== '待审批') {
    ElMessage.warning('仅待审批合同可执行审批')
    return
  }
  const comment = approvalDialog.comment.trim()
  if (!comment) {
    ElMessage.warning('审批意见不能为空')
    return
  }
  approvalDialog.submitting = true
  try {
    const updated = await approveContract(selectedContract.value.id, {
      approval_result: approvalDialog.result,
      comment,
    })
    ElMessage.success(updated.message || '合同审批已提交')
    approvalDialog.visible = false
    await loadContracts(updated.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '合同审批失败')
  } finally {
    approvalDialog.submitting = false
  }
}

onMounted(async () => {
  if (!canViewContracts.value) {
    errorMessage.value = '当前角色无权查看合同管理台'
    return
  }
  await loadContracts()
})
</script>
