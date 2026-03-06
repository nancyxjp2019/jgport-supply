import axios from 'axios'

export const reportsMode = import.meta.env.VITE_REPORTS_MODE === 'proxy' ? 'proxy' : 'demo'

export const httpClient = axios.create({
  baseURL: reportsMode === 'proxy' ? '/proxy-api' : '/api/v1',
  timeout: 8000,
})
