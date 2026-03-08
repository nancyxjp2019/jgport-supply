import { createRouter, createWebHistory } from 'vue-router'

import AdminShell from '@/layouts/AdminShell.vue'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'
import { canRoleExecuteAction, type AdminActionCode } from '@/utils/permissions'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: {
        title: '管理后台登录',
        summary: '登录页与身份透传链路',
      },
    },
    {
      path: '/',
      component: AdminShell,
      redirect: '/dashboard',
      meta: {
        requiresAuth: true,
      },
      children: [
        {
          path: '/dashboard',
          name: 'dashboard',
          component: () => import('@/views/dashboard/OverviewView.vue'),
          meta: {
            requiresAuth: true,
            title: '经营仪表盘',
            summary: '聚焦履约、资金、库存与异常预警',
          },
        },
        {
          path: '/board',
          name: 'board',
          component: () => import('@/views/board/TasksView.vue'),
          meta: {
            requiresAuth: true,
            title: '业务看板',
            summary: '聚焦待补录金额、库存阻塞与合同待关闭',
          },
        },
        {
          path: '/org-companies',
          name: 'org-companies',
          component: () => import('@/views/org-companies/OrgCompaniesView.vue'),
          meta: {
            requiresAuth: true,
            requiredAction: 'org.manage' as AdminActionCode,
            title: '组织与公司管理',
            summary: '维护运营商、客户、供应商、仓库公司档案与归属关系',
          },
        },
        {
          path: '/contracts',
          name: 'contracts',
          component: () => import('@/views/contracts/ContractsView.vue'),
          meta: {
            requiresAuth: true,
            title: '合同管理台',
            summary: '采购/销售合同列表、详情、提审、审批与图谱摘要回看',
          },
        },
        {
          path: '/orders',
          name: 'orders',
          component: () => import('@/views/orders/OrdersView.vue'),
          meta: {
            requiresAuth: true,
            title: '运营订单处理台',
            summary: '销售订单列表、详情与运营财务审批首批处理',
          },
        },
        {
          path: '/funds',
          name: 'funds',
          component: () => import('@/views/funds/FundsView.vue'),
          meta: {
            requiresAuth: true,
            title: '财务资金处理台',
            summary: '收款单与付款单列表、补录、确认与凭证路径回看',
          },
        },
        {
          path: '/inventory',
          name: 'inventory',
          component: () => import('@/views/inventory/InventoryView.vue'),
          meta: {
            requiresAuth: true,
            title: '库存执行跟踪台',
            summary: '入库单与出库单追踪、校验失败回看与执行异常提示',
          },
        },
        {
          path: '/contract-close',
          name: 'contract-close',
          component: () => import('@/views/contract-close/ContractCloseView.vue'),
          meta: {
            requiresAuth: true,
            title: '合同关闭差异台',
            summary: '自动关闭回看、手工关闭入口与差异留痕回看',
          },
        },
        {
          path: '/funds-reconcile',
          name: 'funds-reconcile',
          component: () => import('@/views/funds-reconcile/FundsReconcileView.vue'),
          meta: {
            requiresAuth: true,
            title: '退款核销与资金驳回台',
            summary: '退款待审核流转、退款驳回与单据核销处理',
          },
        },
        {
          path: '/reports-multi-dim',
          name: 'reports-multi-dim',
          component: () => import('@/views/reports-multi-dim/ReportsMultiDimView.vue'),
          meta: {
            requiresAuth: true,
            title: '多维报表与导出台',
            summary: '合同方向/单据状态/退款状态多维汇总与导出任务创建',
          },
        },
        {
          path: '/reports-export-tasks',
          name: 'reports-export-tasks',
          component: () => import('@/views/report-export-tasks/ReportExportTasksView.vue'),
          meta: {
            requiresAuth: true,
            title: '导出任务中心',
            summary: '异步导出任务、导出历史、结果下载与失败重试',
          },
        },
        {
          path: '/report-recompute-tasks',
          name: 'report-recompute-tasks',
          component: () => import('@/views/report-recompute-tasks/ReportRecomputeTasksView.vue'),
          meta: {
            requiresAuth: true,
            title: '汇总重算任务中心',
            summary: '汇总报表手工重算、快照历史回看与失败重试',
          },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  await authStore.bootstrap()

  if (to.name === 'login') {
    if (authStore.isAuthenticated) {
      return { path: '/dashboard' }
    }
    return true
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: {
        redirect: to.fullPath,
      },
    }
  }

  const requiredAction =
    typeof to.meta.requiredAction === 'string'
      ? (to.meta.requiredAction as AdminActionCode)
      : null
  if (requiredAction && !canRoleExecuteAction(authStore.session?.roleCode, requiredAction)) {
    return { path: '/dashboard' }
  }

  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : '管理后台'
  document.title = `JGPort V6 - ${title}`
})

export default router
