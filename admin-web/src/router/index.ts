import { createRouter, createWebHistory } from 'vue-router'

import AdminShell from '@/layouts/AdminShell.vue'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

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
          path: '/orders',
          name: 'orders',
          component: () => import('@/views/orders/OrdersView.vue'),
          meta: {
            requiresAuth: true,
            title: '运营订单处理台',
            summary: '销售订单列表、详情与运营财务审批首批处理',
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
  return true
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : '管理后台'
  document.title = `JGPort V6 - ${title}`
})

export default router
