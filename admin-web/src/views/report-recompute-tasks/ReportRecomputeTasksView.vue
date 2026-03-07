<template>
  <div class="page-stack report-recompute-tasks-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <template v-if="canViewRecomputeTasks">
      <section class="panel-card report-recompute-tasks-hero">
        <div class="report-recompute-tasks-hero__content">
          <div>
            <p class="panel-card__eyebrow">汇总报表口径重算首批</p>
            <h3>手工发起 / 后台重算 / 历史回看 / 失败重试</h3>
            <p>当前仅支持经营仪表盘、业务看板、轻量报表三类汇总快照的手工重算；沿用 `v1` 口径，不开放历史日期回算和跨自然日批量补刷。</p>
          </div>
          <div class="report-recompute-tasks-hero__actions">
            <ElSelect v-model="statusFilter" clearable placeholder="全部任务状态" @change="loadTasks">
              <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </ElSelect>
            <ElButton :loading="loading" @click="loadTasks">刷新任务</ElButton>
            <ElButton plain @click="router.push('/reports-multi-dim')">返回多维报表</ElButton>
          </div>
        </div>
      </section>

      <section v-if="canManageRecomputeTasks" class="panel-card report-recompute-tasks-form-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">手工创建重算任务</p>
            <h3>首批仅支持汇总快照重算</h3>
          </div>
          <span>{{ selectedReportSummary }}</span>
        </header>

        <div class="report-recompute-tasks-form-grid">
          <ElSelect v-model="selectedReportCodes" multiple collapse-tags collapse-tags-tooltip placeholder="选择需重算的汇总报表">
            <ElOption v-for="item in reportCodeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
          <ElInput v-model="reason" maxlength="255" show-word-limit placeholder="请输入本次重算原因，便于审计回看" />
          <ElButton type="primary" :loading="creating" @click="handleCreateTask">创建重算任务</ElButton>
        </div>
        <p class="order-boundary-tip">任务创建权限仅对财务与管理员开放；运营角色继续保留查询与历史回看能力，不开放手工重算入口。</p>
      </section>

      <section class="reports-multi-dim-summary-grid">
        <article class="signal-card signal-card--accent">
          <span>任务总数</span>
          <strong>{{ tasks.length }}</strong>
          <p>当前筛选条件下的汇总重算任务量</p>
        </article>
        <article class="signal-card signal-card--deep">
          <span>已完成</span>
          <strong>{{ completedCount }}</strong>
          <p>已生成新快照并可回看的任务数</p>
        </article>
        <article class="signal-card signal-card--warning">
          <span>需关注</span>
          <strong>{{ failedCount + processingCount }}</strong>
          <p>处理中与失败任务需继续跟进</p>
        </article>
      </section>

      <section class="panel-card report-recompute-tasks-table-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">重算任务历史</p>
            <h3>共 {{ tasks.length }} 条</h3>
          </div>
          <span>{{ latestTaskTime }}</span>
        </header>

        <ElTable v-loading="loading" :data="tasks" row-key="id">
          <ElTableColumn prop="task_name" label="任务名" min-width="150" />
          <ElTableColumn label="状态" min-width="120">
            <template #default="scope">
              <ElTag :type="resolveStatusTagType(scope.row.status)">{{ scope.row.status }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn label="报表范围" min-width="220">
            <template #default="scope">{{ formatReportCodes(scope.row.report_codes) }}</template>
          </ElTableColumn>
          <ElTableColumn prop="reason" label="重算原因" min-width="240" />
          <ElTableColumn prop="retry_count" label="重试次数" min-width="100" />
          <ElTableColumn label="结果快照" min-width="280">
            <template #default="scope">{{ formatResultPayload(scope.row.result_payload) }}</template>
          </ElTableColumn>
          <ElTableColumn label="发起时间" min-width="170">
            <template #default="scope">{{ formatDateTime(scope.row.created_at) }}</template>
          </ElTableColumn>
          <ElTableColumn label="完成时间" min-width="170">
            <template #default="scope">{{ formatDateTime(scope.row.finished_at) }}</template>
          </ElTableColumn>
          <ElTableColumn label="失败原因" min-width="220">
            <template #default="scope">{{ scope.row.error_message || '—' }}</template>
          </ElTableColumn>
          <ElTableColumn label="操作" min-width="160" fixed="right">
            <template #default="scope">
              <ElButton
                size="small"
                :disabled="!canManageRecomputeTasks || scope.row.status !== '已失败'"
                :loading="retryTaskId === scope.row.id"
                @click="handleRetry(scope.row.id)"
              >
                重试任务
              </ElButton>
            </template>
          </ElTableColumn>
        </ElTable>

        <ElEmpty v-if="!loading && !tasks.length" description="当前筛选条件下暂无汇总重算任务" />
      </section>
    </template>

    <section v-else class="panel-card report-recompute-tasks-empty-card">
      <ElEmpty description="当前角色暂无汇总报表重算查看权限" />
      <p class="order-boundary-tip">汇总报表口径重算历史仅对运营、财务与管理员开放；创建与重试动作继续仅对财务与管理员开放。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  ElAlert,
  ElButton,
  ElEmpty,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  createSummaryReportRecomputeTask,
  fetchSummaryReportRecomputeTasks,
  retrySummaryReportRecomputeTask,
  type ReportExportTaskStatus,
  type SummaryReportCode,
  type SummaryReportRecomputeTask,
} from '@/api/reports'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/formatters'
import { canRoleExecuteAction } from '@/utils/permissions'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const creating = ref(false)
const errorMessage = ref('')
const tasks = ref<SummaryReportRecomputeTask[]>([])
const statusFilter = ref<ReportExportTaskStatus | ''>('')
const retryTaskId = ref<number | null>(null)
const selectedReportCodes = ref<SummaryReportCode[]>(['dashboard_summary', 'board_tasks'])
const reason = ref('')

const reportCodeOptions: Array<{ label: string; value: SummaryReportCode }> = [
  { label: '经营仪表盘', value: 'dashboard_summary' },
  { label: '业务看板', value: 'board_tasks' },
  { label: '轻量报表', value: 'light_overview' },
]

const statusOptions: Array<{ label: string; value: ReportExportTaskStatus }> = [
  { label: '待处理', value: '待处理' },
  { label: '处理中', value: '处理中' },
  { label: '已完成', value: '已完成' },
  { label: '已失败', value: '已失败' },
]

const reportCodeLabelMap = Object.fromEntries(reportCodeOptions.map((item) => [item.value, item.label])) as Record<
  SummaryReportCode,
  string
>

const currentRoleCode = computed(() => authStore.session?.roleCode ?? '')
const canViewRecomputeTasks = computed(() =>
  canRoleExecuteAction(currentRoleCode.value, 'reports.summary.recompute.view'),
)
const canManageRecomputeTasks = computed(() =>
  canRoleExecuteAction(currentRoleCode.value, 'reports.summary.recompute'),
)
const completedCount = computed(() => tasks.value.filter((item) => item.status === '已完成').length)
const failedCount = computed(() => tasks.value.filter((item) => item.status === '已失败').length)
const processingCount = computed(() => tasks.value.filter((item) => item.status === '处理中' || item.status === '待处理').length)
const latestTaskTime = computed(() => formatDateTime(tasks.value[0]?.updated_at || null))
const selectedReportSummary = computed(() => formatReportCodes(selectedReportCodes.value))

function resolveStatusTagType(status: ReportExportTaskStatus): 'success' | 'warning' | 'danger' | 'info' {
  if (status === '已完成') {
    return 'success'
  }
  if (status === '已失败') {
    return 'danger'
  }
  if (status === '处理中') {
    return 'warning'
  }
  return 'info'
}

function formatReportCodes(reportCodes: SummaryReportCode[]): string {
  if (!reportCodes.length) {
    return '未选择'
  }
  return reportCodes.map((item) => reportCodeLabelMap[item]).join(' / ')
}

function formatResultPayload(resultPayload: SummaryReportRecomputeTask['result_payload']): string {
  const items = Object.entries(resultPayload)
  if (!items.length) {
    return '—'
  }
  return items
    .map(([reportCode, item]) => {
      const label = reportCodeLabelMap[reportCode as SummaryReportCode] || item.report_name || reportCode
      return `${label}：${formatDateTime(item.snapshot_time)}`
    })
    .join(' / ')
}

async function loadTasks() {
  if (!canViewRecomputeTasks.value) {
    tasks.value = []
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchSummaryReportRecomputeTasks({
      status: statusFilter.value || undefined,
      limit: 30,
    })
    tasks.value = response.items
  } catch (error) {
    tasks.value = []
    errorMessage.value = error instanceof Error ? error.message : '汇总重算任务加载失败'
  } finally {
    loading.value = false
  }
}

async function handleCreateTask() {
  if (!canManageRecomputeTasks.value) {
    ElMessage.warning('当前角色无权创建汇总报表重算任务')
    return
  }
  if (!selectedReportCodes.value.length) {
    ElMessage.warning('请至少选择一个汇总报表')
    return
  }
  if (!reason.value.trim()) {
    ElMessage.warning('请输入重算原因')
    return
  }
  creating.value = true
  try {
    await createSummaryReportRecomputeTask({
      metric_version: 'v1',
      report_codes: selectedReportCodes.value,
      reason: reason.value.trim(),
    })
    ElMessage.success('汇总重算任务已创建，请稍后刷新查看结果')
    reason.value = ''
    await loadTasks()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '汇总重算任务创建失败')
  } finally {
    creating.value = false
  }
}

async function handleRetry(taskId: number) {
  retryTaskId.value = taskId
  try {
    await retrySummaryReportRecomputeTask(taskId)
    ElMessage.success('汇总重算任务已重新发起，请稍后刷新结果')
    await loadTasks()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '汇总重算任务重试失败')
  } finally {
    retryTaskId.value = null
  }
}

defineExpose({
  handleCreateTask,
  handleRetry,
  selectedReportCodes,
  reason,
})

onMounted(async () => {
  await loadTasks()
})
</script>
