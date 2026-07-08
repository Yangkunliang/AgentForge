<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectsApi } from '@/api/modules/projects'
import { useProjectStore } from '@/stores/project'
import type { ProjectMountStatus, ProjectMountType } from '@/types'

const router = useRouter()
const projectStore = useProjectStore()

const currentStep = ref(1)
const projectName = ref('')
const projectDescription = ref('')
const mountMethod = ref<'cli' | 'github' | 'upload'>('cli')
const mountLocator = ref('')
const selectedTags = ref<string[]>([])
const customTag = ref('')
const submitting = ref(false)
const completedMountMethod = ref<'cli' | 'github' | 'upload' | null>(null)
const githubAuthorizationUrl = ref('')
const githubOAuthState = ref('')
const githubOAuthExpiresAt = ref('')

const techTags = [
  'Vue 3', 'React', 'Angular', 'Svelte',
  'FastAPI', 'Django', 'Flask', 'Express', 'NestJS',
  'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
  'Docker', 'Kubernetes', 'AWS', 'Node.js', 'Python',
]

const steps = [
  { id: 1, label: '基本信息' },
  { id: 2, label: '挂载代码库' },
  { id: 3, label: '技术栈标签' },
  { id: 4, label: '完成' },
]

const mountOptions: Array<{
  id: 'cli' | 'github' | 'upload'
  title: string
  desc: string
  icon: 'terminal' | 'github' | 'upload'
}> = [
  { id: 'cli', title: '本地目录 CLI', desc: '通过命令行挂载本地代码目录', icon: 'terminal' },
  { id: 'github', title: 'GitHub OAuth', desc: '连接 GitHub 仓库，自动同步', icon: 'github' },
  { id: 'upload', title: '手动上传', desc: '上传关键文件供 Agent 分析', icon: 'upload' },
]

const isStepValid = computed(() => {
  if (currentStep.value === 1) return projectName.value.trim().length > 0
  if (currentStep.value === 2) {
    if (mountMethod.value === 'github') return isGitHubRepoInputValid(mountLocator.value)
    return mountLocator.value.trim().length > 0
  }
  return true
})

const mountLocatorLabel = computed(() => {
  if (mountMethod.value === 'github') return 'GitHub 仓库'
  if (mountMethod.value === 'upload') return '上传文件标识'
  return '本地目录路径'
})

const mountLocatorPlaceholder = computed(() => {
  if (mountMethod.value === 'github') return '例如：acme/payment-service 或 https://github.com/acme/payment-service'
  if (mountMethod.value === 'upload') return '例如：payment-service.zip'
  return '例如：/Users/me/work/payment-service'
})

const mountLocatorHint = computed(() => {
  if (mountMethod.value === 'github') return '提交后会先创建项目，再生成 GitHub OAuth 授权链接；授权完成后才会创建 connected Mount。'
  if (mountMethod.value === 'upload') return '上传解析将在后续任务实现，这里先保存手动上传的上下文入口。'
  return 'AgentForge 不会自动扫描本机目录，只会使用你明确授权的路径。'
})

const completionTitle = computed(() => {
  if (completedMountMethod.value === 'github' && githubAuthorizationUrl.value) return 'GitHub 授权已准备好'
  return '项目创建成功'
})

const completionDescription = computed(() => {
  if (completedMountMethod.value === 'github' && githubAuthorizationUrl.value) {
    return `${projectName.value || '新项目'} 已创建，继续完成 GitHub 授权后，AgentForge 会把仓库作为主代码库接入项目。`
  }
  return `${projectName.value || '新项目'} 已创建完成`
})

function selectTag(tag: string) {
  const idx = selectedTags.value.indexOf(tag)
  if (idx >= 0) {
    selectedTags.value.splice(idx, 1)
  } else {
    selectedTags.value.push(tag)
  }
}

function addCustomTag() {
  const tag = customTag.value.trim()
  if (tag && !selectedTags.value.includes(tag)) {
    selectedTags.value.push(tag)
    customTag.value = ''
  }
}

function toMountType(): ProjectMountType {
  if (mountMethod.value === 'cli') return 'local'
  return mountMethod.value
}

function toMountStatus(): ProjectMountStatus {
  if (mountMethod.value === 'upload') return 'pending'
  return 'connected'
}

function normalizeGitHubRepoFullName(value: string): string {
  return value
    .trim()
    .replace(/^git@github\.com:/, '')
    .replace(/^https?:\/\/github\.com\//, '')
    .replace(/^github\.com\//, '')
    .replace(/[?#].*$/, '')
    .replace(/\/$/, '')
    .replace(/\.git$/, '')
}

function isGitHubRepoInputValid(value: string): boolean {
  return /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(normalizeGitHubRepoFullName(value))
}

async function submitProject() {
  if (submitting.value) return
  submitting.value = true
  try {
    completedMountMethod.value = null
    githubAuthorizationUrl.value = ''
    githubOAuthState.value = ''
    githubOAuthExpiresAt.value = ''

    const project = await projectStore.createProject({
      name: projectName.value,
      description: projectDescription.value,
      tech_tags: selectedTags.value,
    })
    if (mountMethod.value === 'github') {
      const { data } = await projectsApi.startGitHubOAuthMount(project.id, {
        repo_full_name: normalizeGitHubRepoFullName(mountLocator.value),
        role: 'primary',
        redirect_uri: `${window.location.origin}/api/v1/projects/${project.id}/mounts/github/oauth/callback`,
      })
      githubAuthorizationUrl.value = data.authorization_url
      githubOAuthState.value = data.state
      githubOAuthExpiresAt.value = data.expires_at
    } else {
      await projectStore.createMount(project.id, {
        mount_type: toMountType(),
        display_name: '主代码库',
        locator: mountLocator.value,
        role: 'primary',
        status: toMountStatus(),
        metadata: {
          created_from: 'project_create_wizard',
        },
      })
    }
    completedMountMethod.value = mountMethod.value
    currentStep.value = 4
    ElMessage.success(mountMethod.value === 'github' ? '项目已创建，请完成 GitHub 授权' : '项目已创建')
  } finally {
    submitting.value = false
  }
}

async function nextStep() {
  if (currentStep.value === 3) {
    await submitProject()
    return
  }
  if (currentStep.value < 4) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

function finish() {
  router.push('/chat')
}

function openGitHubAuthorization() {
  if (!githubAuthorizationUrl.value) return
  window.location.href = githubAuthorizationUrl.value
}
</script>

<template>
  <div class="create-project-page">
    <div class="page-container">
      <div class="header">
        <button class="back-btn" @click="router.push('/projects')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          <span>返回</span>
        </button>
        <h1 class="page-title">创建新项目</h1>
      </div>

      <div class="steps-bar">
        <div v-for="step in steps" :key="step.id" class="step-item">
          <div class="step-circle" :class="{ active: currentStep >= step.id, done: currentStep > step.id }">
            <span v-if="currentStep > step.id">✓</span>
            <span v-else>{{ step.id }}</span>
          </div>
          <span class="step-label">{{ step.label }}</span>
          <div v-if="step.id < 4" class="step-connector" :class="{ active: currentStep > step.id }"></div>
        </div>
      </div>

      <div class="form-content">
        <Transition name="fade" mode="out-in">
          <div v-if="currentStep === 1" key="step1" class="step-content">
            <h2 class="step-title">项目基本信息</h2>
            <p class="step-desc">设置项目名称和描述，便于后续管理和识别</p>

            <div class="form-group">
              <label class="form-label">项目名称 <span class="required">*</span></label>
              <input
                v-model="projectName"
                type="text"
                class="form-input"
                placeholder="例如：我的电商后端"
              />
            </div>

            <div class="form-group">
              <label class="form-label">项目描述（可选）</label>
              <textarea
                v-model="projectDescription"
                class="form-textarea"
                placeholder="简要描述这个项目的用途..."
                rows="3"
              />
            </div>
          </div>

          <div v-else-if="currentStep === 2" key="step2" class="step-content">
            <h2 class="step-title">挂载代码库</h2>
            <p class="step-desc">选择一种方式将代码库接入 AgentForge</p>

            <div class="mount-options">
              <div
                v-for="option in mountOptions"
                :key="option.id"
                class="mount-option"
                :class="{ active: mountMethod === option.id }"
                @click="mountMethod = option.id"
              >
                <div class="option-icon">
                  <svg v-if="option.icon === 'terminal'" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
                  </svg>
                  <svg v-else-if="option.icon === 'github'" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M15 22v-4a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v4"/><circle cx="9" cy="9" r="4"/><path d="M21 22v-4a4 4 0 0 0-1-3h-3a4 4 0 0 0-4 4v4"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                  <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </div>
                <div class="option-info">
                  <h3 class="option-title">{{ option.title }}</h3>
                  <p class="option-desc">{{ option.desc }}</p>
                </div>
                <div class="option-radio">
                  <span :class="{ checked: mountMethod === option.id }"></span>
                </div>
              </div>
            </div>

            <div v-if="mountMethod === 'cli'" class="cli-example">
              <pre class="cli-code"><code>$ agentforge mount {{ mountLocator || '/Users/me/work/payment-service' }}</code></pre>
              <p class="cli-hint">复制命令到终端执行，将本地目录挂载到平台</p>
            </div>

            <div v-else-if="mountMethod === 'github'" class="oauth-status" data-testid="github-oauth-status">
              <div class="oauth-status__title">将跳转到 GitHub 授权</div>
              <div class="oauth-status__desc">授权成功后，平台会保存加密凭据并创建 GitHub connected Mount。</div>
            </div>

            <div class="form-group mount-locator-group">
              <label class="form-label">{{ mountLocatorLabel }} <span class="required">*</span></label>
              <input
                v-model="mountLocator"
                type="text"
                class="form-input"
                :placeholder="mountLocatorPlaceholder"
              />
              <p class="mount-locator-hint">{{ mountLocatorHint }}</p>
            </div>
          </div>

          <div v-else-if="currentStep === 3" key="step3" class="step-content">
            <h2 class="step-title">技术栈标签</h2>
            <p class="step-desc">选择项目使用的技术栈，帮助 Agent 更好地理解代码</p>

            <div class="tags-grid">
              <span
                v-for="tag in techTags"
                :key="tag"
                class="tag-item"
                :class="{ selected: selectedTags.includes(tag) }"
                @click="selectTag(tag)"
              >
                {{ tag }}
              </span>
            </div>

            <div class="custom-tag-input">
              <input
                v-model="customTag"
                type="text"
                class="form-input"
                placeholder="输入自定义技术栈标签..."
                @keydown.enter="addCustomTag"
              />
              <button class="btn-secondary" @click="addCustomTag">添加</button>
            </div>

            <div v-if="selectedTags.length > 0" class="selected-tags">
              <span>已选择：</span>
              <span v-for="tag in selectedTags" :key="tag" class="selected-tag">
                {{ tag }}
                <button @click="selectTag(tag)" class="tag-remove">×</button>
              </span>
            </div>
          </div>

          <div v-else key="step4" class="step-content step-complete">
            <div class="complete-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#67c23a" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/><path d="M8 12l3 3 6-6"/>
              </svg>
            </div>
            <h2 class="step-title">{{ completionTitle }}</h2>
            <p class="step-desc">
              {{ completionDescription }}<br/>
              {{ selectedTags.length > 0 ? `技术栈：${selectedTags.join('、')}` : '' }}
            </p>
            <div
              v-if="githubAuthorizationUrl"
              class="github-completion"
              data-testid="github-oauth-completion"
            >
              <div class="github-completion__row">
                <span>授权状态</span>
                <strong>待 GitHub 确认</strong>
              </div>
              <div class="github-completion__row">
                <span>授权 State</span>
                <code>{{ githubOAuthState }}</code>
              </div>
            </div>
            <a
              v-if="githubAuthorizationUrl"
              class="btn-primary btn-large github-oauth-link"
              :href="githubAuthorizationUrl"
              data-testid="github-oauth-link"
              @click.prevent="openGitHubAuthorization"
            >
              <span>继续 GitHub 授权</span>
            </a>
            <button class="btn-secondary btn-large" @click="finish">
              <span>{{ githubAuthorizationUrl ? '稍后进入对话' : '开始第一次对话' }}</span>
            </button>
          </div>
        </Transition>
      </div>

      <div v-if="currentStep < 4" class="footer-actions">
        <button class="btn-secondary" @click="prevStep" :disabled="currentStep === 1">
          <span>上一步</span>
        </button>
        <button class="btn-primary" @click="nextStep" :disabled="!isStepValid || submitting">
          <span>{{ submitting ? '创建中...' : currentStep === 3 ? '完成' : '下一步' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.create-project-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 24px;
}

.page-container {
  max-width: 720px;
  margin: 0 auto;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: transparent;
  border: none;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;

  &:hover { background: #f3f4f6; }
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.steps-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #9ca3af;
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;

  &.active {
    background: #409eff;
    color: #fff;
  }

  &.done {
    background: #67c23a;
    color: #fff;
  }
}

.step-label {
  font-size: 13px;
  color: #6b7280;
  white-space: nowrap;

  @media (max-width: 480px) {
    display: none;
  }
}

.step-connector {
  width: 40px;
  height: 2px;
  background: #e5e7eb;
  margin: 0 12px;
  transition: background 0.2s;

  &.active { background: #67c23a; }
}

.form-content {
  min-height: 300px;
}

.step-content {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px;
}

.step-desc {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}

.required { color: #ef4444; }

.form-input,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  color: #111827;
  transition: border-color 0.15s;

  &:focus {
    outline: none;
    border-color: #409eff;
  }

  &::placeholder { color: #9ca3af; }
}

.form-textarea {
  resize: vertical;
}

.mount-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mount-option {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;

  &:hover { border-color: #d1d5db; }

  &.active {
    border-color: #409eff;
    background: #f0f7ff;
  }
}

.option-icon {
  width: 44px;
  height: 44px;
  background: #f3f4f6;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  flex-shrink: 0;
}

.option-info {
  flex: 1;
}

.option-title {
  font-size: 15px;
  font-weight: 500;
  color: #111827;
  margin: 0 0 4px;
}

.option-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.option-radio {
  width: 20px;
  height: 20px;
  border: 2px solid #d1d5db;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  span {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: transparent;
    transition: background 0.15s;
  }

  .checked { background: #409eff; }
}

.cli-example {
  margin-top: 20px;
  padding: 16px;
  background: #1f2937;
  border-radius: 8px;
}

.cli-code {
  margin: 0;
  font-size: 14px;
  color: #d1d5db;
  font-family: monospace;
}

.cli-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #9ca3af;
}

.oauth-status {
  margin-top: 20px;
  padding: 14px 16px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #eff6ff;
  text-align: left;
}

.oauth-status__title {
  font-size: 14px;
  font-weight: 600;
  color: #1d4ed8;
}

.oauth-status__desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
}

.mount-locator-group {
  margin-top: 16px;
}

.mount-locator-hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}

.tags-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  padding: 6px 12px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 13px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover { background: #e5e7eb; }

  &.selected {
    background: #eff6ff;
    color: #409eff;
  }
}

.custom-tag-input {
  display: flex;
  gap: 8px;
  margin-top: 20px;
}

.custom-tag-input .form-input {
  flex: 1;
}

.btn-secondary {
  padding: 10px 16px;
  background: #f3f4f6;
  color: #6b7280;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover:not(:disabled) { background: #e5e7eb; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.selected-tags {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #6b7280;
}

.selected-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: #eff6ff;
  color: #409eff;
  border-radius: 4px;
  font-size: 12px;
}

.tag-remove {
  width: 16px;
  height: 16px;
  border: none;
  background: transparent;
  color: #409eff;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;

  &:hover { background: rgba(64, 158, 255, 0.1); }
}

.step-complete {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 40px 20px;
}

.complete-icon {
  margin-bottom: 16px;
}

.github-completion {
  width: min(100%, 420px);
  margin-top: 8px;
  padding: 14px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  text-align: left;
}

.github-completion__row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 13px;
  color: #6b7280;

  & + & {
    margin-top: 8px;
  }

  strong {
    color: #b45309;
    font-weight: 600;
  }

  code {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #374151;
    white-space: nowrap;
  }
}

.btn-large {
  margin-top: 16px;
  padding: 12px 24px;
  font-size: 15px;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid #f3f4f6;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s;

  &:hover:not(:disabled) { background: #337ecc; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}
</style>
