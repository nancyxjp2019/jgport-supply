import axios from 'axios'

export const reportsMode = import.meta.env.VITE_REPORTS_MODE === 'proxy' ? 'proxy' : 'demo'

export const httpClient = axios.create({
  baseURL: reportsMode === 'proxy' ? '/proxy-api' : '/api/v1',
  timeout: 8000,
})

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detailMessage =
      error.response?.data?.detail || error.response?.data?.message || error.message || '请求失败，请稍后重试'
    return Promise.reject(new Error(detailMessage))
  },
)
