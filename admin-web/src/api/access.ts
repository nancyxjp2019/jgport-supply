import type { AccessCheckResponse, AccessProfile } from '@/types/auth'

import { httpClient } from './http'

export async function fetchCurrentActor(): Promise<AccessProfile> {
  const { data } = await httpClient.get<AccessProfile>('/access/me')
  return data
}

export async function checkAdminWebAccess(): Promise<AccessCheckResponse> {
  const { data } = await httpClient.post<AccessCheckResponse>('/access/check', {
    target_client_type: 'admin_web',
  })
  return data
}
