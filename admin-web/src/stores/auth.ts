import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { checkAdminWebAccess, fetchCurrentActor } from '@/api/access'
import { reportsMode } from '@/api/http'
import type { AccessProfile, AuthSession } from '@/types/auth'
import {
  AUTH_SESSION_STORAGE_KEY,
  buildDemoSession,
  getRoleLabel,
  isAdminWebAllowedRole,
  parseStoredSession,
} from '@/utils/auth'

function readStoredSession(): AuthSession | null {
  if (typeof window === 'undefined') {
    return null
  }
  return parseStoredSession(window.localStorage.getItem(AUTH_SESSION_STORAGE_KEY))
}

function writeStoredSession(session: AuthSession | null): void {
  if (typeof window === 'undefined') {
    return
  }
  if (!session) {
    window.localStorage.removeItem(AUTH_SESSION_STORAGE_KEY)
    return
  }
  window.localStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session))
}

function buildProxySession(profile: AccessProfile): AuthSession {
  return {
    userId: profile.user_id,
    roleCode: profile.role_code,
    roleLabel: getRoleLabel(profile.role_code),
    companyId: profile.company_id,
    companyType: profile.company_type,
    clientType: profile.client_type,
    loginMode: 'proxy',
  }
}

export const useAuthStore = defineStore('auth', () => {
  const ready = ref(false)
  const loading = ref(false)
  const session = ref<AuthSession | null>(null)
  const proxyProfile = ref<AccessProfile | null>(null)
  const errorMessage = ref('')

  const isAuthenticated = computed(() => session.value !== null)
  const currentRoleLabel = computed(() => session.value?.roleLabel ?? '未登录')

  async function bootstrap() {
    if (ready.value) {
      return
    }
    errorMessage.value = ''
    if (reportsMode === 'demo') {
      session.value = readStoredSession()
      if (
        session.value?.loginMode !== 'demo' ||
        (session.value && !isAdminWebAllowedRole(session.value.roleCode))
      ) {
        session.value = null
        writeStoredSession(null)
      }
      ready.value = true
      return
    }

    const storedSession = readStoredSession()
    if (storedSession?.loginMode !== 'proxy') {
      session.value = null
      writeStoredSession(null)
      ready.value = true
      return
    }

    try {
      const profile = await fetchCurrentActor()
      proxyProfile.value = profile
      if (profile.admin_web_allowed && profile.client_type === 'admin_web') {
        session.value = buildProxySession(profile)
        writeStoredSession(session.value)
      } else {
        session.value = null
        writeStoredSession(null)
      }
    } catch (_error) {
      session.value = null
      writeStoredSession(null)
    }
    ready.value = true
  }

  function loginAsDemo(roleCode: string) {
    errorMessage.value = ''
    const nextSession = buildDemoSession(roleCode)
    session.value = nextSession
    writeStoredSession(nextSession)
    ready.value = true
  }

  async function loadProxyIdentity() {
    loading.value = true
    errorMessage.value = ''
    try {
      proxyProfile.value = await fetchCurrentActor()
      return proxyProfile.value
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '身份读取失败'
      proxyProfile.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  async function loginWithProxy() {
    loading.value = true
    errorMessage.value = ''
    try {
      const profile = proxyProfile.value ?? (await fetchCurrentActor())
      proxyProfile.value = profile
      if (!profile.admin_web_allowed || profile.client_type !== 'admin_web') {
        throw new Error('当前角色不允许登录管理后台')
      }
      await checkAdminWebAccess()
      session.value = buildProxySession(profile)
      writeStoredSession(session.value)
      ready.value = true
      return true
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '管理后台登录失败'
      session.value = null
      writeStoredSession(null)
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    session.value = null
    errorMessage.value = ''
    writeStoredSession(null)
  }

  return {
    bootstrap,
    currentRoleLabel,
    errorMessage,
    isAuthenticated,
    loading,
    loginAsDemo,
    loginWithProxy,
    loadProxyIdentity,
    logout,
    proxyProfile,
    ready,
    session,
  }
})
