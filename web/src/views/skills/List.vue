<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSkillStore } from '@/stores/skill'
import { usePermission } from '@/composables'
import type { InstallSkillForm, MarketplaceSkill } from '@/types'

const skillStore = useSkillStore()
const { canInstallSkills } = usePermission()

// ── 安装对话框 ────────────────────────────────────────────────
const showInstallDialog = ref(false)
const installForm = ref<InstallSkillForm>({ source: '', version: '' })
const installLoading = ref(false)

// ── Tabs ──────────────────────────────────────────────────────
const activeTab = ref<'installed' | 'marketplace'>('installed')

// ── 市场搜索 ──────────────────────────────────────────────────
const marketplaceSource = ref<'all' | 'github' | 'clawhub' | 'local'>('all')
const marketplaceKeyword = ref('')

onMounted(() => {
  skillStore.fetchSkills()
})

function switchTab(tab: 'installed' | 'marketplace') {
  activeTab.value = tab
  if (tab === 'marketplace') {
    loadMarketplace()
  }
}

async function loadMarketplace() {
  await skillStore.fetchMarketplace({
    source: marketplaceSource.value,
    q: marketplaceKeyword.value || undefined,
  })
}

// ── 安装 ──────────────────────────────────────────────────────
function openInstallDialog(prefill?: string) {
  installForm.value = { source: prefill || '', version: '' }
  showInstallDialog.value = true
}

async function handleInstall() {
  if (!installForm.value.source.trim()) {
    ElMessage.warning('请输入 Skill 来源（GitHub URL / PyPI 包名）')
    return
  }
  installLoading.value = true
  try {
    await skillStore.installSkill(installForm.value)
    ElMessage.success('安装任务已创建，请稍候...')
    showInstallDialog.value = false
    installForm.value = { source: '', version: '' }
    startPolling()
  } catch {
    // 错误已在 request 中处理
  } finally {
    installLoading.value = false
  }
}

async function handleInstallFromMarket(item: MarketplaceSkill) {
  try {
    await skillStore.installFromMarketplace(item)
    ElMessage.success(`正在安装 ${item.name}...`)
    startPolling()
    activeTab.value = 'installed'
  } catch {
    // handled
  }
}

function startPolling() {
  const poll = async () => {
    for (const [id, task] of skillStore.installingTasks) {
      if (task.status === 'pending' || task.status === 'installing') {
        await skillStore.pollInstallStatus(id)
      }
    }
    const hasActive = Array.from(skillStore.installingTasks.values()).some(
      (t) => t.status === 'pending' || t.status === 'installing',
    )
    if (hasActive) {
      setTimeout(poll, 2000)
    } else {
      skillStore.fetchSkills()
    }
  }
  poll()
}

// ── 启用 / 禁用 ────────────────────────────────────────────────
async function handleToggleEnable(skillName: string, enabled: boolean) {
  try {
    if (enabled) {
      await skillStore.disableSkill(skillName)
      ElMessage.success(`已禁用 ${skillName}`)
    } else {
      await skillStore.enableSkill(skillName)
      ElMessage.success(`已启用 ${skillName}`)
    }
  } catch {
    // handled
  }
}

// ── 卸载 ──────────────────────────────────────────────────────
async function handleUninstall(skillName: string) {
  try {
    await ElMessageBox.confirm(`确定要卸载 Skill "${skillName}" 吗？`, '确认卸载', {
      confirmButtonText: '卸载',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await skillStore.uninstallSkill(skillName)
    ElMessage.success('卸载成功')
  } catch {
    // user cancelled
  }
}

function sourceLabel(source: string) {
  const map: Record<string, string> = {
    builtin: '内置',
    local: '本地',
    github: 'GitHub',
    pypi: 'PyPI',
    clawhub: 'ClawhHub',
  }
  return map[source] || source
}

function sourceTagType(source: string): string {
  const map: Record<string, string> = {
    builtin: 'info',
    local: '',
    github: 'success',
    pypi: 'warning',
    clawhub: 'danger',
  }
  return map[source] || ''
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}
</script>

<template>
  <div class="skill-list">
    <div class="page-header">
      <h1 class="page-title">Skill 管理</h1>
      <el-button v-if="canInstallSkills" type="primary" @click="openInstallDialog()">
        + 安装 Skill
      </el-button>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" @tab-change="switchTab">
      <!-- ── 已安装 Tab ── -->
      <el-tab-pane label="已安装" name="installed">
        <div class="card">
          <el-table :data="skillStore.skills" v-loading="skillStore.loading" stripe>
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="version" label="版本" width="90" />
            <el-table-column label="来源" width="90">
              <template #default="{ row }">
                <el-tag :type="sourceTagType(row.source_type)" size="small">
                  {{ sourceLabel(row.source_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column label="标签" min-width="140">
              <template #default="{ row }">
                <el-tag
                  v-for="tag in (row.tags || []).slice(0, 3)"
                  :key="tag"
                  size="small"
                  style="margin-right: 4px"
                >
                  {{ tag }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-switch
                  v-if="canInstallSkills"
                  :model-value="row.enabled"
                  size="small"
                  @change="handleToggleEnable(row.name, row.enabled)"
                />
                <el-tag v-else :type="row.enabled ? 'success' : 'info'" size="small">
                  {{ row.enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="安装时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.installed_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button
                  v-if="canInstallSkills && row.source_type !== 'builtin'"
                  type="danger"
                  link
                  size="small"
                  @click="handleUninstall(row.name)"
                >
                  卸载
                </el-button>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 安装进度 -->
        <div v-if="skillStore.installingTasks.size > 0" class="card install-progress">
          <div class="card__header">安装进度</div>
          <div
            v-for="[installId, task] of skillStore.installingTasks"
            :key="installId"
            class="install-task"
          >
            <div class="install-header">
              <span class="install-name">{{ task.skill_name }}</span>
              <el-tag
                :type="task.status === 'done' ? 'success' : task.status === 'failed' ? 'danger' : 'primary'"
                size="small"
              >
                {{ task.status }}
              </el-tag>
            </div>
            <div v-if="task.log" class="install-log">{{ task.log }}</div>
            <div v-if="task.error" class="install-error">{{ task.error }}</div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ── 市场 Tab ── -->
      <el-tab-pane label="Skill 市场" name="marketplace">
        <!-- 筛选栏 -->
        <div class="marketplace-toolbar">
          <el-input
            v-model="marketplaceKeyword"
            placeholder="搜索 Skill..."
            style="width: 280px"
            clearable
            @keyup.enter="loadMarketplace"
          >
            <template #prefix><el-icon>🔍</el-icon></template>
          </el-input>
          <el-select v-model="marketplaceSource" style="width: 140px" @change="loadMarketplace">
            <el-option label="全部来源" value="all" />
            <el-option label="GitHub" value="github" />
            <el-option label="ClawhHub" value="clawhub" />
            <el-option label="本地" value="local" />
          </el-select>
          <el-button @click="loadMarketplace">搜索</el-button>
          <span class="marketplace-count">
            共 {{ skillStore.marketplaceTotal }} 个 Skill
          </span>
        </div>

        <!-- Skill 卡片网格 -->
        <div v-loading="skillStore.marketplaceLoading" class="marketplace-grid">
          <div
            v-for="item in skillStore.marketplaceItems"
            :key="item.name + item.source"
            class="skill-card"
          >
            <div class="skill-card__header">
              <img
                v-if="item.icon"
                :src="item.icon"
                class="skill-card__avatar"
                alt=""
              />
              <div v-else class="skill-card__avatar-placeholder">🔧</div>
              <div class="skill-card__meta">
                <div class="skill-card__name">{{ item.name }}</div>
                <div class="skill-card__author">by {{ item.author }}</div>
              </div>
              <el-tag :type="item.source === 'github' ? 'success' : item.source === 'clawhub' ? 'danger' : ''" size="small">
                {{ item.source === 'github' ? 'GitHub' : item.source === 'clawhub' ? 'ClawhHub' : '本地' }}
              </el-tag>
            </div>

            <p class="skill-card__desc">{{ item.description || '暂无描述' }}</p>

            <div class="skill-card__tags">
              <el-tag
                v-for="tag in item.tags.slice(0, 4)"
                :key="tag"
                size="small"
                type="info"
                style="margin-right: 4px; margin-bottom: 4px"
              >
                {{ tag }}
              </el-tag>
            </div>

            <div class="skill-card__footer">
              <span v-if="item.stars > 0" class="skill-card__stars">⭐ {{ item.stars }}</span>
              <span v-else />
              <div class="skill-card__actions">
                <el-button
                  v-if="item.url"
                  size="small"
                  link
                  type="primary"
                  :href="item.url"
                  target="_blank"
                  tag="a"
                >
                  查看
                </el-button>
                <el-button
                  v-if="canInstallSkills && item.url && item.source !== 'local'"
                  size="small"
                  type="primary"
                  @click="handleInstallFromMarket(item)"
                >
                  安装
                </el-button>
                <el-tag v-else-if="item.source === 'local'" type="success" size="small">
                  已安装
                </el-tag>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="!skillStore.marketplaceLoading && skillStore.marketplaceItems.length === 0" class="marketplace-empty">
            <p>未找到 Skill，尝试换个关键词或来源</p>
            <p class="marketplace-tip">
              💡 在 GitHub 上创建带 <code>agentforge-skill</code> topic 标签的仓库来发布自己的 Skill
            </p>
            <p class="marketplace-tip">
              🔧 配置 <code>CLAWHUB_API_BASE</code> 环境变量来启用 ClawhHub Skill 市场
            </p>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 安装对话框 -->
    <el-dialog v-model="showInstallDialog" title="安装 Skill" width="520px">
      <el-form :model="installForm" label-width="80px">
        <el-form-item label="来源" required>
          <el-input
            v-model="installForm.source"
            placeholder="GitHub URL 或 PyPI 包名"
          />
          <div class="form-hint">
            示例：<code>https://github.com/owner/agentforge-skill-weather</code>
            或 <code>agentforge-skill-calculator</code>
          </div>
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="installForm.version" placeholder="默认 latest" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInstallDialog = false">取消</el-button>
        <el-button type="primary" :loading="installLoading" @click="handleInstall">
          开始安装
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
}

.text-muted {
  color: #c0c4cc;
  font-size: 12px;
}

// ── 安装进度 ──────────────────────────────────────────────────
.install-progress {
  margin-top: $spacing-md;
}

.install-task {
  padding: $spacing-md;
  background: #f5f7fa;
  border-radius: $border-radius-sm;
  margin-bottom: $spacing-sm;

  .install-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $spacing-sm;
  }

  .install-name {
    font-weight: 500;
  }

  .install-log,
  .install-error {
    font-size: 12px;
    font-family: monospace;
    white-space: pre-wrap;
    color: #606266;
    max-height: 100px;
    overflow-y: auto;
  }

  .install-error {
    color: #f56c6c;
  }
}

// ── 市场工具栏 ─────────────────────────────────────────────────
.marketplace-toolbar {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-lg;
  flex-wrap: wrap;
}

.marketplace-count {
  color: #909399;
  font-size: 13px;
  margin-left: auto;
}

.marketplace-empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: #909399;

  .marketplace-tip {
    margin-top: $spacing-sm;
    font-size: 13px;

    code {
      background: #f5f7fa;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
    }
  }
}

// ── Skill 卡片网格 ─────────────────────────────────────────────
.marketplace-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: $spacing-md;
  min-height: 200px;
}

.skill-card {
  border: 1px solid #e4e7ed;
  border-radius: $border-radius-md;
  padding: $spacing-md;
  background: #fff;
  transition: box-shadow 0.2s;
  display: flex;
  flex-direction: column;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  }

  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-sm;
  }

  &__avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
  }

  &__avatar-placeholder {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #f0f2f5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
  }

  &__meta {
    flex: 1;
    min-width: 0;
  }

  &__name {
    font-weight: 600;
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__author {
    font-size: 12px;
    color: #909399;
  }

  &__desc {
    font-size: 13px;
    color: #606266;
    margin: $spacing-sm 0;
    line-height: 1.5;
    flex: 1;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__tags {
    margin-bottom: $spacing-sm;
    min-height: 24px;
  }

  &__footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: auto;
    padding-top: $spacing-sm;
    border-top: 1px solid #f0f2f5;
  }

  &__stars {
    font-size: 12px;
    color: #e6a23c;
  }

  &__actions {
    display: flex;
    gap: $spacing-xs;
    align-items: center;
  }
}

// ── 表单提示 ──────────────────────────────────────────────────
.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.5;

  code {
    background: #f5f7fa;
    padding: 1px 5px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 11px;
  }
}
</style>
