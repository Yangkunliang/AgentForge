<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { agentsApi } from '@/api/modules/agents'
import { uploadApi } from '@/api/modules/sessions'
import UserAvatar from '@/components/common/UserAvatar.vue'

const agentName = ref('CodeSoul')
const fileInputRef = ref<HTMLInputElement | null>(null)
const avatarPreview = ref<string | null>(null)
const saving = ref(false)

const currentAvatarSrc = computed(() => avatarPreview.value || undefined)

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

  const reader = new FileReader()
  reader.onload = (ev) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = 200
      canvas.height = 200
      const ctx = canvas.getContext('2d')!
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

async function saveSettings() {
  saving.value = true
  try {
    let avatarUrl = avatarPreview.value

    if (avatarUrl && avatarUrl.startsWith('data:image/')) {
      const blob = await fetch(avatarUrl).then((res) => res.blob())
      const uploadFile = new File([blob], 'avatar.jpg', { type: 'image/jpeg' })
      const { data } = await uploadApi.image(uploadFile)
      avatarUrl = data.url
    }

    await agentsApi.updateMySettings({
      name: agentName.value.trim() || 'CodeSoul',
      avatar_url: avatarUrl || null,
    })

    avatarPreview.value = avatarUrl
    ElMessage.success('AI 助手设置已更新')
  } finally {
    saving.value = false
  }
}

async function removeAvatar() {
  avatarPreview.value = null
  await saveSettings()
}

async function loadAgent() {
  try {
    const { data } = await agentsApi.getMySettings()
    agentName.value = data.agent_name
    avatarPreview.value = data.avatar_url
  } catch {
    // ignore
  }
}

loadAgent()
</script>

<template>
  <div class="agent-settings">
    <h2 class="page-title">AI 助手设置</h2>

    <section class="section">
      <h3 class="section-title">头像</h3>
      <div class="avatar-row">
        <div class="avatar-preview" @click="openAvatarPicker" title="点击更换头像">
          <UserAvatar
            :name="agentName"
            :avatar-url="currentAvatarSrc"
            :size="80"
            shape="squircle"
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
              :loading="saving"
              @click="saveSettings"
            >
              保存头像
            </el-button>
            <el-button
              v-if="avatarPreview"
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

    <section class="section">
      <h3 class="section-title">助手昵称</h3>
      <p class="section-desc">设置 AI 助手的显示名称，聊天时将显示此昵称</p>
      <div class="inline-form">
        <el-input
          v-model="agentName"
          placeholder="输入昵称，最多 50 字"
          maxlength="50"
          show-word-limit
          style="max-width: 320px"
          @keydown.enter="saveSettings"
        />
        <el-button type="primary" :loading="saving" @click="saveSettings">
          保存
        </el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.agent-settings {
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

.inline-form {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
