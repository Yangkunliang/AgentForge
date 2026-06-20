import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { AxiosError } from 'axios'
import { authApi } from '@/api'
import type { User, LoginForm, RegisterForm } from '@/types'
import router from '@/router'

interface AuthErrorResponse {
  detail?: string | { msg?: string }[]
  message?: string
}

function showAuthError(error: unknown, fallback: string) {
  const axiosErr = error as AxiosError<AuthErrorResponse> | undefined
  const status = axiosErr?.response?.status
  const data = axiosErr?.response?.data
  const detail = data?.detail
  const detailStr = Array.isArray(detail) ? detail.map((d) => d.msg).join('；') : detail
  const message = data?.message

  if (status === 401) {
    ElMessage.error('用户名或密码错误')
    return
  }
  if (status === 409) {
    if (detailStr === 'DUPLICATE_USERNAME') {
      ElMessage.error('用户名已被注册')
      return
    }
    if (detailStr === 'DUPLICATE_EMAIL') {
      ElMessage.error('该邮箱已被注册')
      return
    }
    ElMessage.error(detailStr || '账号已存在')
    return
  }
  if (status === 422) {
    const msg = detailStr && detailStr.length > 0 ? detailStr : '请检查输入格式'
    ElMessage.error(msg)
    return
  }
  if (status === 500) {
    ElMessage.error('服务器错误，请稍后重试')
    return
  }
  if (!axiosErr?.response) {
    ElMessage.error('网络连接失败，请检查网络')
    return
  }
  ElMessage.error(detailStr || message || fallback)
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.permissions.includes('admin') ?? false)

  async function login(form: LoginForm) {
    loading.value = true
    try {
      const { data } = await authApi.login(form)
      token.value = data.access_token
      user.value = data.user
      localStorage.setItem('access_token', data.access_token)
      ElMessage.success('登录成功')
      router.push('/dashboard')
    } catch (error) {
      showAuthError(error, '登录失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function register(form: RegisterForm) {
    loading.value = true
    try {
      const { data } = await authApi.register(form)
      token.value = data.access_token
      user.value = data.user
      localStorage.setItem('access_token', data.access_token)
      ElMessage.success('注册成功')
      router.push('/dashboard')
    } catch (error) {
      showAuthError(error, '注册失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // 忽略错误
    } finally {
      token.value = null
      user.value = null
      localStorage.removeItem('access_token')
      router.push('/login')
    }
  }

  function hasPermission(permission: string): boolean {
    return user.value?.permissions.includes(permission) ?? false
  }

  return {
    token,
    user,
    loading,
    isLoggedIn,
    isAdmin,
    login,
    register,
    logout,
    hasPermission,
  }
})
