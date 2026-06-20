import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

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
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理错误
request.interceptors.response.use(
  (response) => {
    return response
  },
  async (error: AxiosError<{ detail?: string; message?: string }>) => {
    const status = error.response?.status

    switch (status) {
      case 401:
        // Token 过期，尝试刷新
        await silentRefresh()
        break
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
        const message = error.response?.data?.detail || error.response?.data?.message || '请求失败'
        ElMessage.error(message)
    }

    return Promise.reject(error)
  }
)

// Silent refresh token
async function silentRefresh(): Promise<string | null> {
  try {
    const response = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
    const newToken = response.data.access_token
    localStorage.setItem('access_token', newToken)
    return newToken
  } catch {
    // Refresh 失败，清除 token 并跳转登录
    localStorage.removeItem('access_token')
    router.push('/login')
    return null
  }
}

export default request
export { silentRefresh }
