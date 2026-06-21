import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

declare module 'axios' {
  interface AxiosRequestConfig {
    authEndpoint?: boolean
    _retry?: boolean
  }
}

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：注入 Token
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 并发 401 时的队列管理
let isRefreshing = false
let waitingQueue: Array<(token: string) => void> = []

function onRefreshed(token: string) {
  waitingQueue.forEach((cb) => cb(token))
  waitingQueue = []
}

async function silentRefresh(): Promise<string | null> {
  try {
    const response = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
    const newToken = response.data.access_token
    localStorage.setItem('access_token', newToken)
    return newToken
  } catch {
    localStorage.removeItem('access_token')
    router.push('/login')
    return null
  }
}

// 响应拦截器
request.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string | { msg?: string }[]; message?: string }>) => {
    const originalConfig = error.config as InternalAxiosRequestConfig & { _retry?: boolean; authEndpoint?: boolean }

    // auth 接口本身不做自动续期（防止死循环）
    if (originalConfig?.authEndpoint) {
      return Promise.reject(error)
    }

    const status = error.response?.status

    // 401 且还没重试过：自动续期
    if (status === 401 && !originalConfig._retry) {
      originalConfig._retry = true

      if (isRefreshing) {
        // 其他请求已在刚新中，排队等待新 token
        return new Promise((resolve) => {
          waitingQueue.push((token: string) => {
            originalConfig.headers.Authorization = `Bearer ${token}`
            resolve(request(originalConfig))
          })
        })
      }

      isRefreshing = true
      const newToken = await silentRefresh()
      isRefreshing = false

      if (newToken) {
        // 通知队列中等待的请求一并重试
        onRefreshed(newToken)
        // 重试原始请求
        originalConfig.headers.Authorization = `Bearer ${newToken}`
        return request(originalConfig)
      }

      // refresh 失败（已在 silentRefresh 里跳转登录）
      return Promise.reject(error)
    }

    // 其他错误统一提示
    switch (status) {
      case 403:
        ElMessage.error('权限不足')
        break
      case 404:
        ElMessage.error('资源不存在')
        break
      case 429:
        ElMessage.error('请求过于频繁，请稍后再试')
        break
      case 500:
        ElMessage.error('服务器错误')
        break
      default:
        if (status !== 401) {
          const message = error.response?.data?.detail || error.response?.data?.message || '请求失败'
          ElMessage.error(typeof message === 'string' ? message : '请求失败')
        }
    }

    return Promise.reject(error)
  }
)

export default request
export { silentRefresh }
