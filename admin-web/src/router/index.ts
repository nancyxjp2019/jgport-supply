import { createRouter, createWebHistory } from 'vue-router'

import AdminShell from '@/layouts/AdminShell.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AdminShell,
      redirect: '/dashboard',
      children: [
        {
          path: '/dashboard',
          name: 'dashboard',
          component: () => import('@/views/dashboard/OverviewView.vue'),
          meta: {
            title: '经营仪表盘',
            summary: '聚焦履约、资金、库存与异常预警',
          },
        },
        {
          path: '/board',
          name: 'board',
          component: () => import('@/views/board/TasksView.vue'),
          meta: {
            title: '业务看板',
            summary: '聚焦待补录金额、库存阻塞与合同待关闭',
          },
        },
      ],
    },
  ],
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : '管理后台'
  document.title = `JGPort V6 - ${title}`
})

export default router
