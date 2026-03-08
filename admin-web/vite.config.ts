import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5666,
      proxy: {
        '/proxy-api': {
          target: env.BACKEND_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/proxy-api/, ''),
          headers: {
            'X-Auth-Secret': env.BACKEND_AUTH_SECRET || '',
            'X-User-Id': env.BACKEND_AUTH_USER_ID || 'DEV-OPS-001',
            'X-Role-Code': env.BACKEND_AUTH_ROLE_CODE || 'operations',
            'X-Company-Id': env.BACKEND_AUTH_COMPANY_ID || 'DEV-OPERATOR-COMPANY',
            'X-Company-Type': env.BACKEND_AUTH_COMPANY_TYPE || 'operator_company',
            'X-Client-Type': env.BACKEND_AUTH_CLIENT_TYPE || 'admin_web',
          },
        },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ['vue', 'vue-router', 'pinia'],
            element: ['element-plus', '@element-plus/icons-vue'],
            axios: ['axios'],
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      include: ['src/**/*.spec.ts'],
      testTimeout: 20000,
    },
  }
})
