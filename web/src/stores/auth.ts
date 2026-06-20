import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'
import type { User, LoginForm, RegisterForm } from '@/types'
import router from '@/router'

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
