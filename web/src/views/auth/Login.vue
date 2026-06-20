<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { LoginForm } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive<LoginForm>({
  username: '',
  password: '',
})

async function handleSubmit() {
  try {
    await authStore.login(form)
  } catch {
    // 错误已在 store 中处理
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="title">AgentForge</h1>
      <p class="subtitle">多智能体协同框架</p>

      <el-form :model="form" class="login-form" @submit.prevent="handleSubmit">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="authStore.loading"
            class="submit-btn"
            native-type="submit"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="footer">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: $spacing-xl * 2;
  background: #fff;
  border-radius: $border-radius-lg;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.title {
  text-align: center;
  font-size: 28px;
  font-weight: 600;
  color: #409eff;
  margin: 0 0 $spacing-sm;
}

.subtitle {
  text-align: center;
  color: #909399;
  margin: 0 0 $spacing-xl;
}

.login-form {
  margin-top: $spacing-lg;
}

.submit-btn {
  width: 100%;
}

.footer {
  text-align: center;
  margin-top: $spacing-lg;
  color: #606266;

  a {
    color: #409eff;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
