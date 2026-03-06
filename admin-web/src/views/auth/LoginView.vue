<template>
  <div class="login-page">
    <section class="login-hero">
      <p class="login-hero__eyebrow">M8-03 身份链路</p>
      <h1>管理后台登录入口</h1>
      <p>
        这一轮先完成管理后台身份闭环：登录页、路由守卫、代理身份读取和服务端权限校验，
        让后续合同、订单、资金、库存页面能直接挂到统一登录态上。
      </p>
      <div class="login-hero__meta">
        <span class="meta-pill">{{ modeLabel }}</span>
        <span class="meta-pill meta-pill--subtle">{{ modeHint }}</span>
      </div>
    </section>

    <section class="login-panel">
      <ElAlert
        v-if="authStore.errorMessage"
        type="error"
        :closable="false"
        :title="authStore.errorMessage"
      />

      <template v-if="isDemoMode">
        <header class="login-panel__header">
          <div>
            <p class="login-panel__eyebrow">演示模式</p>
            <h2>选择管理后台角色</h2>
          </div>
          <span class="login-panel__tip">仅运营、财务、管理员可登录</span>
        </header>

        <div class="login-role-grid">
          <article v-for="item in demoRoles" :key="item.roleCode" class="login-role-card">
            <div>
              <h3>{{ item.roleLabel }}</h3>
              <p>{{ item.description }}</p>
            </div>
            <ElButton type="primary" round @click="handleDemoLogin(item.roleCode)">进入系统</ElButton>
          </article>
        </div>
      </template>

      <template v-else>
        <header class="login-panel__header">
          <div>
            <p class="login-panel__eyebrow">代理联调模式</p>
            <h2>读取当前服务端身份</h2>
          </div>
          <ElButton plain round :loading="authStore.loading" @click="loadProxyIdentity">刷新身份</ElButton>
        </header>

        <div v-if="authStore.proxyProfile" class="proxy-profile-card">
          <div class="proxy-profile-row">
            <span>当前角色</span>
            <strong>{{ currentProxyRoleLabel }}</strong>
          </div>
          <div class="proxy-profile-row">
            <span>公司范围</span>
            <strong>{{ authStore.proxyProfile.company_type }}</strong>
          </div>
          <div class="proxy-profile-row">
            <span>客户端</span>
            <strong>{{ authStore.proxyProfile.client_type }}</strong>
          </div>
          <div class="proxy-profile-row">
            <span>后台权限</span>
            <strong>{{ authStore.proxyProfile.admin_web_allowed ? '允许登录' : '禁止登录' }}</strong>
          </div>
        </div>
        <ElEmpty v-else description="尚未读取到服务端身份" />

        <div class="login-panel__actions">
          <ElButton type="primary" round :loading="authStore.loading" @click="handleProxyLogin">验证并进入系统</ElButton>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElAlert, ElButton, ElEmpty } from 'element-plus'
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { reportsMode } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { ADMIN_WEB_DEMO_ROLES, getRoleLabel } from '@/utils/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const isDemoMode = reportsMode === 'demo'
const demoRoles = ADMIN_WEB_DEMO_ROLES
const modeLabel = computed(() => (isDemoMode ? '演示模式' : '代理联调模式'))
const modeHint = computed(() =>
  isDemoMode ? '本地仅模拟登录角色，不访问后端。' : '由 Vite 开发代理在服务端注入身份头，浏览器不暴露密钥。',
)
const currentProxyRoleLabel = computed(() => getRoleLabel(authStore.proxyProfile?.role_code ?? ''))

function getRedirectPath() {
  const redirect = route.query.redirect
  return typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/dashboard'
}

function handleDemoLogin(roleCode: string) {
  authStore.loginAsDemo(roleCode)
  router.replace(getRedirectPath())
}

async function loadProxyIdentity() {
  await authStore.loadProxyIdentity()
}

async function handleProxyLogin() {
  const success = await authStore.loginWithProxy()
  if (success) {
    await router.replace(getRedirectPath())
  }
}

onMounted(async () => {
  if (!isDemoMode && !authStore.proxyProfile && !authStore.loading) {
    await authStore.loadProxyIdentity()
  }
})
</script>
