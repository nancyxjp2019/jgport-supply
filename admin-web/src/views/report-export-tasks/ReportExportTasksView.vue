<template>
  <div class="page-stack report-export-tasks-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <template v-if="canManageExportTasks">
      <section class="panel-card report-export-tasks-hero">
        <div class="report-export-tasks-hero__content">
          <div>
            <p class="panel-card__eyebrow">导出编排任务中心首批</p>
            <h3>异步导出 / 历史回看 / 下载重试</h3>
            <p>当前仅承接多维报表 CSV 导出任务，支持任务历史回看、结果下载与失败重试，不开放跨报表批量编排。</p>
          </div>
          <div class="report-export-tasks-hero__actions">
            <ElSelect v-model="statusFilter" clearable placeholder="全部任务状态" @change="loadTasks">
              <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </ElSelect>
            <ElButton :loading="loading" @click="loadTasks">刷新任务</ElButton>
            <ElButton type="primary" plain @click="router.push('/reports-multi-dim')">返回多维报表</ElButton>
          </div>
        </div>
      </section>

      <section class="reports-multi-dim-summary-grid">
        <article class="signal-card signal-card--accent">
          <span>任务总数</span>
          <strong>{{ tasks.length }}</strong>
          <p>当前筛选条件下的导出任务总量</p>
        </article>
        <article class="signal-card signal-card--deep">
          <span>已完成</span>
          <strong>{{ completedCount }}</strong>
          <p>可直接下载结果文件的任务数</p>
        </article>
        <article class="signal-card signal-card--warning">
          <span>需关注</span>
          <strong>{{ failedCount + processingCount }}</strong>
          <p>处理中与失败任务需继续跟进</p>
        </article>
      </section>

      <section class="panel-card report-export-tasks-table-card">
        <header class="panel-card__header">
          <div>
            <p class="panel-card__eyebrow">导出任务历史</p>
            <h3>共 {{ tasks.length }} 条</h3>
          </div>
          <span>{{ latestTaskTime }}</span>
        </header>

        <ElTable v-loading="loading" :data="tasks" row-key="id">
          <ElTableColumn prop="report_name" label="报表" min-width="120" />
          <ElTableColumn label="状态" min-width="120">
            <template #default="scope">
              <ElTag :type="resolveStatusTagType(scope.row.status)">{{ scope.row.status }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn label="筛选快照" min-width="280">
            <template #default="scope">{{ formatFilters(scope.row.filters) }}</template>
          </ElTableColumn>
          <ElTableColumn prop="retry_count" label="重试次数" min-width="100" />
          <ElTableColumn prop="download_count" label="下载次数" min-width="100" />
          <ElTableColumn label="发起时间" min-width="170">
            <template #default="scope">{{ formatDateTime(scope.row.created_at) }}</template>
          </ElTableColumn>
          <ElTableColumn label="完成时间" min-width="170">
            <template #default="scope">{{ formatDateTime(scope.row.finished_at) }}</template>
          </ElTableColumn>
          <ElTableColumn label="失败原因" min-width="220">
            <template #default="scope">{{ scope.row.error_message || '—' }}</template>
          </ElTableColumn>
          <ElTableColumn label="操作" min-width="220" fixed="right">
            <template #default="scope">
              <div class="report-export-tasks-actions">
                <ElButton
                  size="small"
                  type="primary"
                  plain
                  :disabled="scope.row.status !== '已完成'"
                  :loading="downloadTaskId === scope.row.id"
                  @click="handleDownload(scope.row.id, scope.row.file_name)"
                >
                  下载结果
                </ElButton>
                <ElButton
                  size="small"
                  :disabled="scope.row.status !== '已失败'"
                  :loading="retryTaskId === scope.row.id"
                  @click="handleRetry(scope.row.id)"
                >
                  重试导出
                </ElButton>
              </div>
            </template>
          </ElTableColumn>
        </ElTable>

        <ElEmpty v-if="!loading && !tasks.length" description="当前筛选条件下暂无导出任务" />
        <p class="order-boundary-tip">首批仅支持多维报表 CSV 导出任务；已完成任务可重复下载，失败任务可手工重试。</p>
      </section>
    </template>

    <section v-else class="panel-card report-export-tasks-empty-card">
      <ElEmpty description="当前角色暂无导出任务中心权限" />
      <p class="order-boundary-tip">导出任务中心仅对财务与管理员开放，运营角色继续保留多维报表查询能力。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  ElAlert,
  ElButton,
  ElEmpty,
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
  downloadAdminMultiDimExportTask,
  fetchAdminMultiDimExportTasks,
  retryAdminMultiDimExportTask,
  type AdminMultiDimExportTask,
  type ReportExportTaskStatus,
} from '@/api/reports'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/formatters'
import { canRoleExecuteAction } from '@/utils/permissions'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const errorMessage = ref('')
const tasks = ref<AdminMultiDimExportTask[]>([])
const statusFilter = ref<ReportExportTaskStatus | ''>('')
const downloadTaskId = ref<number | null>(null)
const retryTaskId = ref<number | null>(null)

const currentRoleCode = computed(() => authStore.session?.roleCode ?? '')
const canManageExportTasks = computed(() =>
  canRoleExecuteAction(currentRoleCode.value, 'reports.multi_dim.export'),
)

const statusOptions: Array<{ label: string; value: ReportExportTaskStatus }> = [
  { label: '待处理', value: '待处理' },
  { label: '处理中', value: '处理中' },
  { label: '已完成', value: '已完成' },
  { label: '已失败', value: '已失败' },
]

const completedCount = computed(() => tasks.value.filter((item) => item.status === '已完成').length)
const failedCount = computed(() => tasks.value.filter((item) => item.status === '已失败').length)
const processingCount = computed(() => tasks.value.filter((item) => item.status === '处理中' || item.status === '待处理').length)
const latestTaskTime = computed(() => formatDateTime(tasks.value[0]?.updated_at || null))

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

function formatFilters(filters: Record<string, string | null>): string {
  const labels = [
    `分组：${filters.group_by || 'contract_direction'}`,
    `合同方向：${filters.contract_direction || '全部'}`,
    `单据状态：${filters.doc_status || '全部'}`,
    `退款状态：${filters.refund_status || '全部'}`,
    `日期：${filters.date_from || '不限'} ~ ${filters.date_to || '不限'}`,
  ]
  return labels.join(' / ')
}

async function loadTasks() {
  if (!canManageExportTasks.value) {
    tasks.value = []
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchAdminMultiDimExportTasks({
      status: statusFilter.value || undefined,
      limit: 30,
    })
    tasks.value = response.items
  } catch (error) {
    tasks.value = []
    errorMessage.value = error instanceof Error ? error.message : '导出任务加载失败'
  } finally {
    loading.value = false
  }
}

async function handleDownload(taskId: number, fileName: string | null) {
  downloadTaskId.value = taskId
  try {
    const fileBlob = await downloadAdminMultiDimExportTask(taskId)
    const objectUrl = URL.createObjectURL(fileBlob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = fileName || `multi-dim-report-task-${taskId}.csv`
    anchor.click()
    URL.revokeObjectURL(objectUrl)
    ElMessage.success('导出文件下载已开始')
    await loadTasks()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导出文件下载失败')
  } finally {
    downloadTaskId.value = null
  }
}

async function handleRetry(taskId: number) {
  retryTaskId.value = taskId
  try {
    await retryAdminMultiDimExportTask(taskId)
    ElMessage.success('导出任务已重新发起，请稍后刷新结果')
    await loadTasks()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导出任务重试失败')
  } finally {
    retryTaskId.value = null
  }
}

onMounted(async () => {
  await loadTasks()
})
</script>
