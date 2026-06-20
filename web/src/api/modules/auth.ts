import request from '../request'
import type { LoginForm, RegisterForm, AuthResponse } from '@/types'

export const authApi = {
  login: (data: LoginForm) => {
    return request.post<AuthResponse>('/auth/login', data)
  },

  register: (data: RegisterForm) => {
    return request.post<AuthResponse>('/auth/register', data)
  },

  refresh: () => {
    return request.post<{ access_token: string }>('/auth/refresh')
  },

  logout: () => {
    return request.post('/auth/logout')
  },
}
