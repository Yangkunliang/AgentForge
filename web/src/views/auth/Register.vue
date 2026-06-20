<script setup lang="ts">
import { reactive } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { RegisterForm } from '@/types'

const authStore = useAuthStore()

const form = reactive<RegisterForm>({
  username: '',
  email: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  try {
    await authStore.register(form)
  } catch {
    // 错误已在 store 中处理
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <h1 class="title">注册</h1>
      <p class="subtitle">创建 AgentForge 账号</p>

      <el-form :model="form" :rules="rules" class="register-form" @submit.prevent="handleSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="邮箱" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="authStore.loading" class="submit-btn" native-type="submit">
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="footer">
        已有账号？
        <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.register-card {
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

.register-form {
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
