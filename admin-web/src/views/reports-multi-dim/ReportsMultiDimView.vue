<template>
  <div class="page-stack reports-multi-dim-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <section class="panel-card reports-multi-dim-filter-card">
      <div class="reports-multi-dim-filter-row">
        <div>
          <p class="panel-card__eyebrow">多维报表与导出首批</p>
          <h3>维度汇总 / 筛选 / CSV 导出</h3>
          <p>首批支持合同方向、单据状态、退款状态维度汇总与导出，不开放多维钻取重算与批量任务编排。</p>
        </div>
        <div class="reports-multi-dim-filter-actions">
          <ElSelect v-model="groupBy" class="reports-multi-dim-filter-select" @change="reloadReport">
            <ElOption v-for="item in groupByOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect
            v-model="contractDirection"
            class="reports-multi-dim-filter-select"
            clearable
            placeholder="全部合同方向"
            @change="reloadReport"
          >
            <ElOption v-for="item in contractDirectionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect v-model="docStatus" class="reports-multi-dim-filter-select" clearable placeholder="全部单据状态" @change="reloadReport">
            <ElOption v-for="item in docStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElSelect
            v-model="refundStatus"
            class="reports-multi-dim-filter-select"
            clearable
            placeholder="全部退款状态"
            @change="reloadReport"
          >
            <ElOption v-for="item in refundStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElDatePicker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            @change="reloadReport"
          />
          <ElButton type="primary" :loading="loading" @click="reloadReport">刷新报表</ElButton>
          <ElButton :disabled="!canExportMultiDim" :loading="exporting" @click="handleExport">导出 CSV</ElButton>
        </div>
      </div>
    </section>

    <section class="reports-multi-dim-summary-grid">
      <article class="signal-card signal-card--accent">
        <span>收款净额</span>
        <strong>¥{{ formatMoney(report?.total_receipt_net_amount || '0') }}</strong>
        <p>当前筛选范围下的收款净额汇总</p>
      </article>
      <article class="signal-card signal-card--deep">
        <span>付款净额</span>
        <strong>¥{{ formatMoney(report?.total_payment_net_amount || '0') }}</strong>
        <p>当前筛选范围下的付款净额汇总</p>
      </article>
      <article class="signal-card signal-card--warning">
        <span>资金净流入</span>
        <strong>¥{{ formatMoney(report?.total_net_cashflow || '0') }}</strong>
        <p>收款净额减付款净额</p>
      </article>
    </section>

    <section class="panel-card reports-multi-dim-table-card">
      <header class="panel-card__header">
        <div>
          <p class="panel-card__eyebrow">多维明细</p>
          <h3>{{ groupByLabel }}共 {{ report?.rows.length ?? 0 }} 组</h3>
        </div>
        <span>{{ formatDateTime(report?.snapshot_time || null) }}</span>
      </header>

      <ElTable v-loading="loading" :data="report?.rows || []" row-key="dimension_value">
        <ElTableColumn prop="dimension_value" label="维度值" min-width="140" />
        <ElTableColumn label="收款净额" min-width="130">
          <template #default="scope">¥{{ formatMoney(scope.row.receipt_net_amount) }}</template>
        </ElTableColumn>
        <ElTableColumn label="付款净额" min-width="130">
          <template #default="scope">¥{{ formatMoney(scope.row.payment_net_amount) }}</template>
        </ElTableColumn>
        <ElTableColumn label="资金净流入" min-width="130">
          <template #default="scope">¥{{ formatMoney(scope.row.net_cashflow) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="receipt_doc_count" label="收款单数" min-width="110" />
        <ElTableColumn prop="payment_doc_count" label="付款单数" min-width="110" />
        <ElTableColumn prop="pending_supplement_count" label="待补录数量" min-width="120" />
        <ElTableColumn prop="refund_pending_review_count" label="待审核退款数量" min-width="140" />
      </ElTable>

      <ElEmpty v-if="!loading && !(report?.rows.length)" description="当前筛选条件下暂无多维数据" />
      <p v-if="!canExportMultiDim" class="order-boundary-tip">当前角色仅可查看多维报表，暂无导出按钮权限。</p>
      <p class="order-boundary-tip">首批仅支持单页筛选与 CSV 导出，不开放多维钻取、口径重算与定时编排任务管理。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  ElAlert,
  ElButton,
  ElDatePicker,
  ElEmpty,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
} from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import {
  exportAdminMultiDimReportCsv,
  fetchAdminMultiDimReport,
  type AdminMultiDimGroupBy,
  type AdminMultiDimReportResponse,
} from '@/api/reports'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, formatMoney } from '@/utils/formatters'
import { canRoleExecuteAction } from '@/utils/permissions'

const groupByOptions: Array<{ label: string; value: AdminMultiDimGroupBy }> = [
  { label: '合同方向', value: 'contract_direction' },
  { label: '单据状态', value: 'doc_status' },
  { label: '退款状态', value: 'refund_status' },
]

const contractDirectionOptions = [
  { label: '销售', value: 'sales' },
  { label: '采购', value: 'purchase' },
]

const docStatusOptions = [
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
const exporting = ref(false)
const errorMessage = ref('')
const report = ref<AdminMultiDimReportResponse | null>(null)

const groupBy = ref<AdminMultiDimGroupBy>('contract_direction')
const contractDirection = ref<'sales' | 'purchase' | ''>('')
const docStatus = ref('')
const refundStatus = ref('')
const dateRange = ref<[string, string] | null>(null)
const authStore = useAuthStore()
const currentRoleCode = computed(() => authStore.session?.roleCode ?? '')
const canExportMultiDim = computed(() => canRoleExecuteAction(currentRoleCode.value, 'reports.multi_dim.export'))

const groupByLabel = computed(() => groupByOptions.find((item) => item.value === groupBy.value)?.label ?? '多维')

const requestQuery = computed(() => ({
  group_by: groupBy.value,
  contract_direction: contractDirection.value || undefined,
  doc_status: docStatus.value || undefined,
  refund_status: refundStatus.value || undefined,
  date_from: dateRange.value?.[0] || undefined,
  date_to: dateRange.value?.[1] || undefined,
}))

async function reloadReport() {
  loading.value = true
  errorMessage.value = ''
  try {
    report.value = await fetchAdminMultiDimReport(requestQuery.value)
  } catch (error) {
    report.value = null
    errorMessage.value = error instanceof Error ? error.message : '多维报表加载失败'
  } finally {
    loading.value = false
  }
}

async function handleExport() {
  if (!canExportMultiDim.value) {
    ElMessage.warning('当前角色无权执行多维报表导出动作')
    return
  }
  exporting.value = true
  try {
    const fileBlob = await exportAdminMultiDimReportCsv(requestQuery.value)
    const objectUrl = URL.createObjectURL(fileBlob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = `multi-dim-report-${Date.now()}.csv`
    anchor.click()
    URL.revokeObjectURL(objectUrl)
    ElMessage.success('CSV 导出已开始')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'CSV 导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await reloadReport()
})
</script>
