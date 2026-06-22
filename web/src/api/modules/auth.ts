import request from '../request'
import type { LoginForm, RegisterForm, AuthResponse } from '@/types'

export const authApi = {
  login: (data: LoginForm) => {
    return request.post<AuthResponse>('/auth/login', data, {
      authEndpoint: true,
    })
  },

  register: (data: RegisterForm) => {
    return request.post<AuthResponse>('/auth/register', data, {
      authEndpoint: true,
    })
  },

  refresh: () => {
    return request.post<{ access_token: string }>('/auth/refresh')
  },

  logout: () => {
    return request.post('/auth/logout')
  },

  me: () => {
    return request.get<{ user: import('@/types').User }>('/auth/me')
  },

  updateProfile: (data: { nickname?: string | null; avatar_url?: string | null; current_password?: string; new_password?: string }) => {
    return request.patch<{ user: import('@/types').User }>('/auth/me', data)
  },
}
