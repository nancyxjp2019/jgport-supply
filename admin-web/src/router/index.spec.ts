import { beforeEach, describe, expect, it } from 'vitest'

import router from './index'
import { useAuthStore } from '@/stores/auth'
import { pinia } from '@/stores'
import { AUTH_SESSION_STORAGE_KEY, buildDemoSession } from '@/utils/auth'

const protectedRoutes = [
  { name: 'dashboard', path: '/dashboard', title: '经营仪表盘' },
  { name: 'board', path: '/board', title: '业务看板' },
  { name: 'org-companies', path: '/org-companies', title: '组织与公司管理' },
  { name: 'contracts', path: '/contracts', title: '合同管理台' },
  { name: 'orders', path: '/orders', title: '运营订单处理台' },
  { name: 'funds', path: '/funds', title: '财务资金处理台' },
  { name: 'inventory', path: '/inventory', title: '库存执行跟踪台' },
  { name: 'contract-close', path: '/contract-close', title: '合同关闭差异台' },
  { name: 'funds-reconcile', path: '/funds-reconcile', title: '退款核销与资金驳回台' },
  { name: 'reports-multi-dim', path: '/reports-multi-dim', title: '多维报表与导出台' },
  { name: 'reports-export-tasks', path: '/reports-export-tasks', title: '导出任务中心' },
  { name: 'report-recompute-tasks', path: '/report-recompute-tasks', title: '汇总重算任务中心' },
] as const

function resetAuthState() {
  const authStore = useAuthStore(pinia)
  authStore.ready = false
  authStore.loading = false
  authStore.session = null
  authStore.proxyProfile = null
  authStore.errorMessage = ''
  window.localStorage.clear()
}

function restoreDemoSession(roleCode: 'operations' | 'finance' | 'admin') {
  resetAuthState()
  const authStore = useAuthStore(pinia)
  const session = buildDemoSession(roleCode)
  authStore.session = session
  authStore.ready = true
  window.localStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session))
}

describe('router', () => {
  beforeEach(async () => {
    resetAuthState()
    await router.replace('/login')
    document.title = 'JGPort V6'
  })

  it('核心页面路由都带受保护标记与中文标题摘要', () => {
    const loginRoute = router.getRoutes().find((route) => route.name === 'login')
    expect(loginRoute?.meta.title).toBe('管理后台登录')
    expect(loginRoute?.meta.summary).toBe('登录页与身份透传链路')

    protectedRoutes.forEach((expectedRoute) => {
      const route = router.getRoutes().find((item) => item.name === expectedRoute.name)
      expect(route?.path).toBe(expectedRoute.path)
      expect(route?.meta.requiresAuth).toBe(true)
      expect(route?.meta.title).toBe(expectedRoute.title)
      expect(typeof route?.meta.summary).toBe('string')
      expect(String(route?.meta.summary).length).toBeGreaterThan(0)
    })
  })

  it('未登录访问受保护页面会跳转到登录页并保留 redirect', async () => {
    await router.push('/reports-export-tasks')

    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/reports-export-tasks')
    expect(document.title).toBe('JGPort V6 - 管理后台登录')
  })

  it('已登录后访问登录页会回跳到仪表盘', async () => {
    restoreDemoSession('finance')

    await router.push('/login?from=spec')

    expect(router.currentRoute.value.path).toBe('/dashboard')
    expect(document.title).toBe('JGPort V6 - 经营仪表盘')
  })

  it('切换业务页面后会同步更新浏览器标题', async () => {
    restoreDemoSession('operations')

    await router.push('/board')
    expect(document.title).toBe('JGPort V6 - 业务看板')

    await router.push('/contract-close')
    expect(document.title).toBe('JGPort V6 - 合同关闭差异台')
  })

  it('非管理员访问组织与公司管理会被路由守卫拦回仪表盘', async () => {
    restoreDemoSession('finance')

    await router.push('/org-companies')

    expect(router.currentRoute.value.path).toBe('/dashboard')
    expect(document.title).toBe('JGPort V6 - 经营仪表盘')
  })
})
