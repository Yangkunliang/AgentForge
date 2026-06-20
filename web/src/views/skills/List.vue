<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSkillStore } from '@/stores/skill'
import { usePermission } from '@/composables'
import type { InstallSkillForm } from '@/types'

const skillStore = useSkillStore()
const { canInstallSkills } = usePermission()

const showInstallDialog = ref(false)
const installForm = ref<InstallSkillForm>({ source: '', version: '' })
const installLoading = ref(false)

onMounted(() => {
  skillStore.fetchSkills()
})

function openInstallDialog() {
  showInstallDialog.value = true
}

async function handleInstall() {
  if (!installForm.value.source.trim()) {
    ElMessage.warning('请输入 Skill 源')
    return
  }

  installLoading.value = true
  try {
    await skillStore.installSkill(installForm.value)
    ElMessage.success('安装任务已创建')
    showInstallDialog.value = false
    installForm.value = { source: '', version: '' }

    // 开始轮询安装状态
    pollInstallStatus()
  } catch {
    // 错误已在 request 中处理
  } finally {
    installLoading.value = false
  }
}

async function pollInstallStatus() {
  for (const [installId, task] of skillStore.installingTasks) {
    if (task.status === 'pending' || task.status === 'installing') {
      await skillStore.pollInstallStatus(installId)
    }
  }

  // 继续轮询直到完成
  const hasActiveTasks = Array.from(skillStore.installingTasks.values()).some(
    (t) => t.status === 'pending' || t.status === 'installing'
  )
  if (hasActiveTasks) {
    setTimeout(pollInstallStatus, 2000)
  } else {
    // 刷新 Skill 列表
    skillStore.fetchSkills()
  }
}

async function handleUninstall(skillName: string) {
  try {
    await ElMessageBox.confirm(`确定要卸载 Skill "${skillName}" 吗?`, '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await skillStore.uninstallSkill(skillName)
    ElMessage.success('卸载成功')
  } catch {
    // 用户取消
  }
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}
</script>

<template>
  <div class="skill-list">
    <div class="page-header">
      <h1 class="page-title">Skill 管理</h1>
      <el-button v-if="canInstallSkills" type="primary" @click="openInstallDialog">
        安装 Skill
      </el-button>
    </div>

    <div class="card">
      <el-table :data="skillStore.skills" v-loading="skillStore.loading">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="entry_point" label="入口" />
        <el-table-column prop="installed_at" label="安装时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.installed_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="canInstallSkills"
              type="danger"
              link
              size="small"
              @click="handleUninstall(row.name)"
            >
              卸载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 安装进度 -->
    <div v-if="skillStore.installingTasks.size > 0" class="card">
      <div class="card__header">安装进度</div>
      <div v-for="[installId, task] of skillStore.installingTasks" :key="installId" class="install-task">
        <div class="install-header">
          <span>{{ task.skill_name }}</span>
          <el-tag :type="task.status === 'done' ? 'success' : task.status === 'failed' ? 'danger' : 'primary'" size="small">
            {{ task.status }}
          </el-tag>
        </div>
        <div v-if="task.log" class="install-log">{{ task.log }}</div>
        <div v-if="task.error" class="install-error">{{ task.error }}</div>
      </div>
    </div>

    <!-- 安装对话框 -->
    <el-dialog v-model="showInstallDialog" title="安装 Skill" width="500px">
      <el-form :model="installForm" label-width="80px">
        <el-form-item label="源" required>
          <el-input v-model="installForm.source" placeholder="PyPI 包名或 Git URL" />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="installForm.version" placeholder="latest" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showInstallDialog = false">取消</el-button>
        <el-button type="primary" :loading="installLoading" @click="handleInstall">
          安装
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

  .install-log,
  .install-error {
    font-size: 12px;
    font-family: monospace;
    white-space: pre-wrap;
    color: #606266;
  }

  .install-error {
    color: #f56c6c;
  }
}
</style>
