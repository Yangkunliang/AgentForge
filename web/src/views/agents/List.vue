<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { usePermission } from '@/composables'

const router = useRouter()
const agentStore = useAgentStore()
const { canManageAgents } = usePermission()

onMounted(() => {
  agentStore.fetchAgents()
})

function goToCreate() {
  router.push('/agents/create')
}

function getStatusTagType(status: string): string {
  return status === 'active' ? 'success' : 'info'
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}
</script>

<template>
  <div class="agent-list">
    <div class="page-header">
      <h1 class="page-title">Agent 管理</h1>
      <el-button v-if="canManageAgents" type="primary" @click="goToCreate">
        创建 Agent
      </el-button>
    </div>

    <div class="card">
      <el-table :data="agentStore.agents" v-loading="agentStore.loading">
        <el-table-column prop="agent_id" label="ID" width="180" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="capabilities" label="能力" width="200">
          <template #default="{ row }">
            <el-tag v-for="cap in row.capabilities.slice(0, 2)" :key="cap" size="small" class="mr-1">
              {{ cap }}
            </el-tag>
            <span v-if="row.capabilities.length > 2">+{{ row.capabilities.length - 2 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="model" label="模型" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
}

.mr-1 {
  margin-right: $spacing-xs;
}
</style>
