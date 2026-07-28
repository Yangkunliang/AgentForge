<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { RegisterForm } from '@/types'

const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const form = reactive<RegisterForm>({
  username: '',
  email: '',
  password: '',
})

const rules: FormRules<RegisterForm> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3到50个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含英文字母、数字和下划线', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码至少8个字符', trigger: 'blur' },
    { pattern: /[A-Z]/, message: '密码必须包含大写字母', trigger: 'blur' },
    { pattern: /[a-z]/, message: '密码必须包含小写字母', trigger: 'blur' },
    { pattern: /\d/, message: '密码必须包含数字', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return
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

      <el-form ref="formRef" :model="form" :rules="rules" class="register-form" @submit.prevent="handleSubmit">
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
