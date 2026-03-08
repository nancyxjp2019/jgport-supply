<template>
  <div class="shell">
    <aside class="shell__rail">
      <div class="brand-card">
        <p class="brand-card__eyebrow">运营驾驶舱</p>
        <h1>JGPORT V6</h1>
        <p>页面结构持续对齐当前生产化主线口径，当前已落地经营首页、业务看板、组织与公司管理、合同管理台、订单处理台、资金处理台、库存执行跟踪台、合同关闭差异台、退款核销台、多维报表台、导出任务中心与汇总重算任务中心。</p>
      </div>

      <nav class="shell__nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="shell__nav-item"
          active-class="is-active"
        >
          <span class="shell__nav-title">{{ item.label }}</span>
          <span class="shell__nav-summary">{{ item.summary }}</span>
        </RouterLink>
      </nav>

      <div class="shell__mode-card">
        <span class="shell__mode-label">当前模式</span>
        <strong>{{ modeLabel }}</strong>
        <p>{{ modeHint }}</p>
      </div>
    </aside>

    <main class="shell__main">
      <header class="shell__topbar">
        <div>
          <p class="shell__topbar-eyebrow">管理后台首批页面</p>
          <h2>{{ routeTitle }}</h2>
          <p>{{ routeSummary }}</p>
        </div>
        <div class="shell__topbar-meta">
          <span class="meta-pill">{{ modeLabel }}</span>
          <span class="meta-pill meta-pill--subtle">当前登录：{{ currentRoleLabel }}</span>
          <ElButton plain round @click="handleLogout">退出登录</ElButton>
        </div>
      </header>

      <section class="shell__content">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ElButton } from 'element-plus'
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { reportsMode } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { canRoleExecuteAction } from '@/utils/permissions'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = computed(() => [
  {
    to: '/dashboard',
    label: '经营仪表盘',
    summary: '聚焦履约、资金、库存与异常预警',
  },
  {
    to: '/board',
    label: '业务看板',
    summary: '聚焦待补录金额、库存阻塞与合同待关闭',
  },
  {
    to: '/org-companies',
    label: '组织与公司管理',
    summary: '维护运营商、客户、供应商、仓库公司档案与归属关系',
    hidden: !canRoleExecuteAction(authStore.session?.roleCode, 'org.manage'),
  },
  {
    to: '/contracts',
    label: '合同管理台',
    summary: '采购销售合同列表、详情、提审审批与图谱回看',
    hidden: !canRoleExecuteAction(authStore.session?.roleCode, 'contracts.view'),
  },
  {
    to: '/orders',
    label: '运营订单处理台',
    summary: '销售订单列表、详情与运营财务审批处理',
  },
  {
    to: '/funds',
    label: '财务资金处理台',
    summary: '收款单付款单列表、补录确认与凭证路径回看',
  },
  {
    to: '/inventory',
    label: '库存执行跟踪台',
    summary: '入库出库追踪、校验失败回看与执行异常提示',
  },
  {
    to: '/contract-close',
    label: '合同关闭差异台',
    summary: '自动关闭回看、手工关闭入口与差异留痕回看',
  },
  {
    to: '/funds-reconcile',
    label: '退款核销与资金驳回台',
    summary: '退款待审核、退款驳回与单据核销处理',
  },
  {
    to: '/reports-multi-dim',
    label: '多维报表与导出台',
    summary: '合同方向/单据状态/退款状态汇总与导出任务创建',
  },
  {
    to: '/reports-export-tasks',
    label: '导出任务中心',
    summary: '异步导出任务、历史回看、结果下载与失败重试',
    hidden: !canRoleExecuteAction(authStore.session?.roleCode, 'reports.multi_dim.export'),
  },
  {
    to: '/report-recompute-tasks',
    label: '汇总重算任务中心',
    summary: '汇总快照手工重算、历史回看与失败重试',
    hidden: !canRoleExecuteAction(authStore.session?.roleCode, 'reports.summary.recompute.view'),
  },
].filter((item) => !item.hidden))

const routeTitle = computed(() => (typeof route.meta.title === 'string' ? route.meta.title : '管理后台'))
const routeSummary = computed(() =>
  typeof route.meta.summary === 'string' ? route.meta.summary : '聚焦运营与财务协同场景',
)
const modeLabel = computed(() => (reportsMode === 'proxy' ? '代理联调模式' : '演示模式'))
const currentRoleLabel = computed(() => authStore.currentRoleLabel)
const modeHint = computed(() =>
  reportsMode === 'proxy'
    ? '由开发代理在服务端注入身份头，本地联调时不在浏览器暴露密钥。'
    : '使用本地演示数据，便于在登录体系未落地前先评审页面。',
)

async function handleLogout() {
  authStore.logout()
  await router.replace('/login')
}
</script>
