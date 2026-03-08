<template>
  <div class="page-stack org-page">
    <ElAlert v-if="errorMessage" class="page-alert" type="error" :closable="false" :title="errorMessage" />

    <section v-if="!canManageCompanies" class="panel-card org-boundary-card">
      <div class="panel-card__header">
        <div>
          <p class="panel-card__eyebrow">组织与公司管理</p>
          <h3>当前角色无权维护公司档案</h3>
        </div>
      </div>
      <p class="order-boundary-tip">本页首批仅向管理员开放，用于补齐真实业务测试前的组织与公司治理能力。</p>
    </section>

    <template v-else>
      <section class="panel-card org-filter-card">
        <div class="org-filter-row">
          <div>
            <p class="panel-card__eyebrow">G1-01 前置治理基座</p>
            <h3>组织与公司管理</h3>
            <p>首批支持运营商、客户、供应商、仓库公司的建档、归属关系维护、启停用与基础回看。</p>
          </div>
          <div class="org-filter-actions">
            <ElSelect v-model="companyTypeFilter" class="org-filter-select" clearable placeholder="全部公司类型" @change="reloadCompanies">
              <ElOption v-for="item in companyTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </ElSelect>
            <ElSelect v-model="statusFilter" class="org-filter-select" clearable placeholder="全部状态" @change="reloadCompanies">
              <ElOption v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </ElSelect>
            <ElButton type="primary" :loading="loading" @click="reloadCompanies">刷新列表</ElButton>
            <ElButton type="success" @click="openCreateDialog('operator_company')">新建运营商</ElButton>
            <ElButton @click="openCreateDialog('customer_company')">新建客户</ElButton>
            <ElButton @click="openCreateDialog('supplier_company')">新建供应商</ElButton>
            <ElButton @click="openCreateDialog('warehouse_company')">新建仓库</ElButton>
          </div>
        </div>
      </section>

      <section class="org-main-grid">
        <article class="panel-card org-list-card">
          <header class="panel-card__header">
            <div>
              <p class="panel-card__eyebrow">公司列表</p>
              <h3>共 {{ companyList.length }} 家</h3>
            </div>
            <span>按类型与编码排序</span>
          </header>

          <ElTable
            v-loading="loading"
            :data="companyList"
            row-key="company_id"
            highlight-current-row
            @current-change="handleCurrentChange"
          >
            <ElTableColumn prop="company_id" label="公司编码" min-width="180" />
            <ElTableColumn prop="company_name" label="公司名称" min-width="160" />
            <ElTableColumn label="公司类型" min-width="130">
              <template #default="scope">
                {{ resolveCompanyTypeLabel(scope.row.company_type) }}
              </template>
            </ElTableColumn>
            <ElTableColumn label="归属运营商" min-width="160">
              <template #default="scope">
                {{ scope.row.parent_company_name || '--' }}
              </template>
            </ElTableColumn>
            <ElTableColumn label="状态" min-width="110">
              <template #default="scope">
                <ElTag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.status }}</ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn prop="child_company_count" label="启用中下级" min-width="120" />
          </ElTable>
        </article>

        <article class="panel-card org-detail-card">
          <header class="panel-card__header">
            <div>
              <p class="panel-card__eyebrow">公司详情</p>
              <h3>{{ selectedCompany?.company_name || '未选择公司' }}</h3>
            </div>
            <ElTag v-if="selectedCompany" :type="selectedCompany.is_active ? 'success' : 'info'">{{ selectedCompany.status }}</ElTag>
          </header>

          <ElEmpty v-if="!selectedCompany" description="请选择一家公司查看详情" />

          <template v-else>
            <div class="org-detail-grid">
              <div class="detail-row">
                <span>公司编码</span>
                <strong>{{ selectedCompany.company_id }}</strong>
              </div>
              <div class="detail-row">
                <span>公司名称</span>
                <strong>{{ selectedCompany.company_name }}</strong>
              </div>
              <div class="detail-row">
                <span>公司类型</span>
                <strong>{{ resolveCompanyTypeLabel(selectedCompany.company_type) }}</strong>
              </div>
              <div class="detail-row">
                <span>归属运营商</span>
                <strong>{{ selectedCompany.parent_company_name || '--' }}</strong>
              </div>
              <div class="detail-row">
                <span>备注</span>
                <strong>{{ selectedCompany.remark || '暂无' }}</strong>
              </div>
              <div class="detail-row">
                <span>启用中下级公司</span>
                <strong>{{ selectedCompany.child_company_count }}</strong>
              </div>
              <div class="detail-row">
                <span>创建人</span>
                <strong>{{ selectedCompany.created_by }}</strong>
              </div>
              <div class="detail-row">
                <span>更新人</span>
                <strong>{{ selectedCompany.updated_by }}</strong>
              </div>
              <div class="detail-row">
                <span>创建时间</span>
                <strong>{{ formatDateTime(selectedCompany.created_at) }}</strong>
              </div>
              <div class="detail-row">
                <span>更新时间</span>
                <strong>{{ formatDateTime(selectedCompany.updated_at) }}</strong>
              </div>
            </div>

            <div class="org-action-row">
              <ElButton @click="openEditDialog">编辑档案</ElButton>
              <ElButton
                v-if="selectedCompany.is_active"
                type="warning"
                @click="openStatusDialog(false)"
              >
                停用公司
              </ElButton>
              <ElButton
                v-else
                type="success"
                @click="openStatusDialog(true)"
              >
                启用公司
              </ElButton>
            </div>

            <p class="order-boundary-tip">首批不支持物理删除、批量导入导出与复杂集团组织树；非运营商公司必须归属到启用中的运营商公司。</p>
          </template>
        </article>
      </section>
    </template>

    <ElDialog v-model="editorDialog.visible" width="720" :title="editorDialog.mode === 'create' ? '新建公司档案' : '编辑公司档案'">
      <ElForm label-position="top">
        <ElFormItem label="公司编码">
          <ElInput v-model="editorDialog.companyId" maxlength="64" :disabled="editorDialog.mode === 'edit'" placeholder="请输入公司编码" />
        </ElFormItem>
        <ElFormItem label="公司名称">
          <ElInput v-model="editorDialog.companyName" maxlength="128" placeholder="请输入公司名称" />
        </ElFormItem>
        <ElFormItem label="公司类型">
          <ElSelect v-model="editorDialog.companyType" class="org-dialog-select" :disabled="editorDialog.mode === 'edit'" @change="handleEditorCompanyTypeChange">
            <ElOption v-for="item in companyTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="归属运营商">
          <ElSelect
            v-model="editorDialog.parentCompanyId"
            class="org-dialog-select"
            :disabled="editorDialog.companyType === 'operator_company'"
            clearable
            placeholder="请选择归属运营商"
          >
            <ElOption v-for="item in operatorCompanies" :key="item.company_id" :label="item.company_name" :value="item.company_id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="备注">
          <ElInput
            v-model="editorDialog.remark"
            maxlength="256"
            show-word-limit
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文备注"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editorDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="editorDialog.submitting" @click="submitEditorDialog">
          {{ editorDialog.mode === 'create' ? '确认创建' : '保存修改' }}
        </ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="statusDialog.visible" width="560" :title="statusDialog.enabled ? '启用公司' : '停用公司'">
      <ElForm label-position="top">
        <ElFormItem label="公司编码">
          <ElInput :model-value="selectedCompany?.company_id || ''" disabled />
        </ElFormItem>
        <ElFormItem label="变更原因">
          <ElInput
            v-model="statusDialog.reason"
            maxlength="256"
            show-word-limit
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="请输入中文变更原因"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="statusDialog.visible = false">取消</ElButton>
        <ElButton type="primary" :loading="statusDialog.submitting" @click="submitStatusDialog">
          确认提交
        </ElButton>
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
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import {
  createCompany,
  fetchCompanies,
  fetchCompanyDetail,
  updateCompany,
  updateCompanyStatus,
  type CompanyDetailResponse,
  type CompanyListItem,
} from '@/api/companies'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/formatters'
import { canRoleExecuteAction } from '@/utils/permissions'

const companyTypeOptions = [
  { label: '运营商公司', value: 'operator_company' },
  { label: '客户公司', value: 'customer_company' },
  { label: '供应商公司', value: 'supplier_company' },
  { label: '仓库公司', value: 'warehouse_company' },
]
const statusOptions = [
  { label: '启用', value: '启用' },
  { label: '停用', value: '停用' },
]

const loading = ref(false)
const errorMessage = ref('')
const companyTypeFilter = ref('')
const statusFilter = ref('')
const companyList = ref<CompanyListItem[]>([])
const operatorCompanies = ref<CompanyListItem[]>([])
const selectedCompanyId = ref<string | null>(null)
const selectedCompany = ref<CompanyDetailResponse | null>(null)

const editorDialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  companyId: '',
  companyName: '',
  companyType: 'operator_company',
  parentCompanyId: '',
  remark: '',
  submitting: false,
})

const statusDialog = reactive({
  visible: false,
  enabled: false,
  reason: '',
  submitting: false,
})

const authStore = useAuthStore()
const currentRoleCode = computed(() => authStore.session?.roleCode ?? '')
const canManageCompanies = computed(() => canRoleExecuteAction(currentRoleCode.value, 'org.manage'))

function resolveCompanyTypeLabel(companyType: string): string {
  const target = companyTypeOptions.find((item) => item.value === companyType)
  return target?.label || companyType
}

function handleEditorCompanyTypeChange(companyType: string) {
  if (companyType === 'operator_company') {
    editorDialog.parentCompanyId = ''
  }
}

function openCreateDialog(companyType: string) {
  if (!canManageCompanies.value) {
    return
  }
  if (companyType !== 'operator_company' && !operatorCompanies.value.length) {
    ElMessage.warning('请先创建至少一家启用中的运营商公司')
    return
  }
  editorDialog.visible = true
  editorDialog.mode = 'create'
  editorDialog.companyId = ''
  editorDialog.companyName = ''
  editorDialog.companyType = companyType
  editorDialog.parentCompanyId = ''
  editorDialog.remark = ''
}

function openEditDialog() {
  if (!selectedCompany.value) {
    ElMessage.warning('请先选择一家公司')
    return
  }
  editorDialog.visible = true
  editorDialog.mode = 'edit'
  editorDialog.companyId = selectedCompany.value.company_id
  editorDialog.companyName = selectedCompany.value.company_name
  editorDialog.companyType = selectedCompany.value.company_type
  editorDialog.parentCompanyId = selectedCompany.value.parent_company_id || ''
  editorDialog.remark = selectedCompany.value.remark || ''
}

function openStatusDialog(enabled: boolean) {
  if (!selectedCompany.value) {
    ElMessage.warning('请先选择一家公司')
    return
  }
  statusDialog.visible = true
  statusDialog.enabled = enabled
  statusDialog.reason = ''
}

function handleCurrentChange(row: CompanyListItem | undefined) {
  if (!row) {
    return
  }
  selectedCompanyId.value = row.company_id
  void loadCompanyDetail(row.company_id)
}

async function loadOperatorCompanies() {
  const response = await fetchCompanies({ company_type: 'operator_company', status: '启用' })
  operatorCompanies.value = response.items
}

async function loadCompanyDetail(companyId: string) {
  selectedCompany.value = await fetchCompanyDetail(companyId)
}

async function reloadCompanies() {
  if (!canManageCompanies.value) {
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetchCompanies({
      company_type: companyTypeFilter.value || undefined,
      status: statusFilter.value || undefined,
    })
    companyList.value = response.items
    await loadOperatorCompanies()
    const currentTarget = companyList.value.find((item) => item.company_id === selectedCompanyId.value)
    const nextTarget = currentTarget || companyList.value[0]
    if (nextTarget) {
      selectedCompanyId.value = nextTarget.company_id
      await loadCompanyDetail(nextTarget.company_id)
    } else {
      selectedCompanyId.value = null
      selectedCompany.value = null
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '公司列表加载失败'
  } finally {
    loading.value = false
  }
}

async function submitEditorDialog() {
  if (!canManageCompanies.value) {
    return
  }
  editorDialog.submitting = true
  errorMessage.value = ''
  try {
    if (editorDialog.mode === 'create') {
      const created = await createCompany({
        company_id: editorDialog.companyId,
        company_name: editorDialog.companyName,
        company_type: editorDialog.companyType,
        parent_company_id: editorDialog.companyType === 'operator_company' ? undefined : editorDialog.parentCompanyId || undefined,
        remark: editorDialog.remark || undefined,
      })
      ElMessage.success(created.message)
      selectedCompanyId.value = created.company_id
    } else {
      const updated = await updateCompany(editorDialog.companyId, {
        company_name: editorDialog.companyName,
        parent_company_id: editorDialog.companyType === 'operator_company' ? undefined : editorDialog.parentCompanyId || undefined,
        remark: editorDialog.remark || undefined,
      })
      ElMessage.success(updated.message)
      selectedCompanyId.value = updated.company_id
    }
    editorDialog.visible = false
    await reloadCompanies()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '公司档案保存失败'
  } finally {
    editorDialog.submitting = false
  }
}

async function submitStatusDialog() {
  if (!selectedCompany.value || !canManageCompanies.value) {
    return
  }
  statusDialog.submitting = true
  errorMessage.value = ''
  try {
    const updated = await updateCompanyStatus(selectedCompany.value.company_id, {
      enabled: statusDialog.enabled,
      reason: statusDialog.reason,
    })
    ElMessage.success(updated.message)
    statusDialog.visible = false
    selectedCompanyId.value = updated.company_id
    await reloadCompanies()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '公司状态变更失败'
  } finally {
    statusDialog.submitting = false
  }
}

onMounted(() => {
  if (!canManageCompanies.value) {
    return
  }
  void reloadCompanies()
})
</script>

<style scoped>
.org-filter-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.org-filter-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
}

.org-filter-select,
.org-dialog-select {
  width: 180px;
}

.org-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 20px;
}

.org-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 18px;
}

.org-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 20px;
}

@media (max-width: 1200px) {
  .org-main-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .org-filter-row {
    flex-direction: column;
  }

  .org-filter-actions {
    justify-content: flex-start;
  }

  .org-detail-grid {
    grid-template-columns: 1fr;
  }

  .org-filter-select,
  .org-dialog-select {
    width: 100%;
  }
}
</style>
