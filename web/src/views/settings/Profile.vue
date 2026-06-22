<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import UserAvatar from '@/components/common/UserAvatar.vue'

const authStore = useAuthStore()

// ── 昵称 ─────────────────────────────────────────────────────
const nickname = ref(authStore.user?.nickname || '')
const savingProfile = ref(false)

async function saveNickname() {
  savingProfile.value = true
  try {
    await authStore.updateProfile({ nickname: nickname.value.trim() || null })
  } finally {
    savingProfile.value = false
  }
}

// ── 头像 ─────────────────────────────────────────────────────
const fileInputRef = ref<HTMLInputElement | null>(null)
const avatarPreview = ref<string | null>(null)  // 裁剪后的 base64
const uploadingAvatar = ref(false)

function openAvatarPicker() {
  fileInputRef.value?.click()
}

function onAvatarFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!fileInputRef.value) fileInputRef.value = null
  if (e.target instanceof HTMLInputElement) e.target.value = ''
  if (!file) return

  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('图片不超过 2MB')
    return
  }

  // 用 Canvas 压缩到 200×200
  const reader = new FileReader()
  reader.onload = (ev) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = 200
      canvas.height = 200
      const ctx = canvas.getContext('2d')!
      // 居中裁剪
      const size = Math.min(img.width, img.height)
      const sx = (img.width - size) / 2
      const sy = (img.height - size) / 2
      ctx.drawImage(img, sx, sy, size, size, 0, 0, 200, 200)
      avatarPreview.value = canvas.toDataURL('image/jpeg', 0.85)
    }
    img.src = ev.target?.result as string
  }
  reader.readAsDataURL(file)
}

async function saveAvatar() {
  if (!avatarPreview.value) return
  uploadingAvatar.value = true
  try {
    await authStore.updateProfile({ avatar_url: avatarPreview.value })
    avatarPreview.value = null
    ElMessage.success('头像已更新')
  } finally {
    uploadingAvatar.value = false
  }
}

async function removeAvatar() {
  await authStore.updateProfile({ avatar_url: '' })
  avatarPreview.value = null
}

// 当前展示的头像：优先预览，其次已保存的
const currentAvatarSrc = computed(() =>
  avatarPreview.value || authStore.user?.avatar_url || undefined
)
const currentDisplayName = computed(() => authStore.displayName)

// ── 密码修改 ─────────────────────────────────────────────────
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showCurrentPwd = ref(false)
const showNewPwd = ref(false)
const savingPassword = ref(false)

async function savePassword() {
  if (!newPassword.value || !currentPassword.value) return
  if (newPassword.value !== confirmPassword.value) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  savingPassword.value = true
  try {
    await authStore.updateProfile({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    })
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    ElMessage.success('密码已修改')
  } catch {
    // error handled in store
  } finally {
    savingPassword.value = false
  }
}
</script>

<template>
  <div class="profile-settings">
    <h2 class="page-title">个人资料</h2>

    <!-- ── 头像区 ───────────────────────────────────────────── -->
    <section class="section">
      <h3 class="section-title">头像</h3>
      <div class="avatar-row">
        <div class="avatar-preview" @click="openAvatarPicker" title="点击更换头像">
          <UserAvatar
            :name="currentDisplayName"
            :avatar-url="currentAvatarSrc"
            :size="80"
            shape="circle"
          />
          <div class="avatar-overlay">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
              <circle cx="12" cy="13" r="4"/>
            </svg>
          </div>
        </div>

        <div class="avatar-actions">
          <p class="avatar-hint">点击头像上传，支持 JPG / PNG，建议正方形，最大 2MB</p>
          <div class="avatar-btns">
            <el-button size="small" @click="openAvatarPicker">选择图片</el-button>
            <el-button
              v-if="avatarPreview"
              type="primary"
              size="small"
              :loading="uploadingAvatar"
              @click="saveAvatar"
            >
              保存头像
            </el-button>
            <el-button
              v-if="authStore.user?.avatar_url && !avatarPreview"
              type="danger"
              plain
              size="small"
              @click="removeAvatar"
            >
              移除头像
            </el-button>
          </div>
        </div>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        style="display:none"
        @change="onAvatarFileChange"
      />
    </section>

    <!-- ── 昵称区 ───────────────────────────────────────────── -->
    <section class="section">
      <h3 class="section-title">显示昵称</h3>
      <p class="section-desc">设置后聊天头像将显示昵称首字，留空则使用账号用户名「{{ authStore.user?.username }}」</p>
      <div class="inline-form">
        <el-input
          v-model="nickname"
          placeholder="输入昵称，最多 50 字"
          maxlength="50"
          show-word-limit
          style="max-width: 320px"
          @keydown.enter="saveNickname"
        />
        <el-button type="primary" :loading="savingProfile" @click="saveNickname">
          保存
        </el-button>
      </div>
    </section>

    <!-- ── 账号信息（只读） ────────────────────────────────── -->
    <section class="section">
      <h3 class="section-title">账号信息</h3>
      <el-descriptions :column="1" border size="small" class="account-info">
        <el-descriptions-item label="用户名">{{ authStore.user?.username }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ authStore.user?.email }}</el-descriptions-item>
        <el-descriptions-item label="权限">
          <el-tag
            v-for="p in authStore.user?.permissions"
            :key="p"
            size="small"
            style="margin-right: 4px"
          >{{ p }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </section>

    <!-- ── 修改密码 ─────────────────────────────────────────── -->
    <section class="section">
      <h3 class="section-title">修改密码</h3>
      <el-form label-width="100px" class="pwd-form">
        <el-form-item label="当前密码">
          <el-input
            v-model="currentPassword"
            :type="showCurrentPwd ? 'text' : 'password'"
            placeholder="输入当前密码"
            style="max-width: 320px"
          >
            <template #suffix>
              <el-icon style="cursor:pointer" @click="showCurrentPwd = !showCurrentPwd">
                <View v-if="!showCurrentPwd" /><Hide v-else />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="newPassword"
            :type="showNewPwd ? 'text' : 'password'"
            placeholder="至少 8 位，含大小写字母和数字"
            style="max-width: 320px"
          >
            <template #suffix>
              <el-icon style="cursor:pointer" @click="showNewPwd = !showNewPwd">
                <View v-if="!showNewPwd" /><Hide v-else />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="confirmPassword"
            type="password"
            placeholder="再次输入新密码"
            style="max-width: 320px"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="savingPassword"
            :disabled="!currentPassword || !newPassword || !confirmPassword"
            @click="savePassword"
          >
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </section>
  </div>
</template>

<style scoped lang="scss">
.profile-settings {
  max-width: 680px;
  padding: 0 4px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 28px;
}

.section {
  margin-bottom: 36px;
  padding-bottom: 36px;
  border-bottom: 1px solid #f0f0f0;

  &:last-child {
    border-bottom: none;
    margin-bottom: 0;
  }
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 12px;
}

.section-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 12px;
}

// ── 头像区 ────────────────────────────────────────────────────
.avatar-row {
  display: flex;
  align-items: center;
  gap: 24px;
}

.avatar-preview {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  flex-shrink: 0;

  &:hover .avatar-overlay {
    opacity: 1;
  }
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.18s;
}

.avatar-hint {
  font-size: 12px;
  color: #9ca3af;
  margin: 0 0 12px;
  line-height: 1.5;
}

.avatar-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

// ── 昵称 ─────────────────────────────────────────────────────
.inline-form {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

// ── 账号信息 ──────────────────────────────────────────────────
.account-info {
  max-width: 480px;
}

// ── 密码表单 ─────────────────────────────────────────────────
.pwd-form {
  :deep(.el-form-item__label) {
    font-size: 13px;
    color: #374151;
  }
}
</style>
