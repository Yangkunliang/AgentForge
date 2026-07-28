<script setup lang="ts">
import { reactive, onMounted, watch } from 'vue'

interface KeyedGroup {
  key: string
  items: string[]
}

const props = defineProps<{
  modelValue: Record<string, string[]>
  placeholder?: string
  addLabel?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: Record<string, string[]>): void }>()

const groups = reactive<KeyedGroup[]>([])

onMounted(() => {
  const rec = props.modelValue || {}
  groups.splice(
    0,
    groups.length,
    ...Object.entries(rec).map(([k, v]) => ({ key: k, items: [...v] })),
  )
})

function add() {
  groups.push({ key: '', items: [''] })
}
function removeGroup(i: number) {
  groups.splice(i, 1)
}
function addItem(g: KeyedGroup) {
  g.items.push('')
}
function removeItem(g: KeyedGroup, j: number) {
  g.items.splice(j, 1)
}

watch(
  groups,
  () => {
    const rec: Record<string, string[]> = {}
    for (const g of groups) {
      const key = g.key.trim()
      if (!key) continue
      const items = g.items.filter((x) => x.trim() !== '')
      if (items.length) rec[key] = items
    }
    emit('update:modelValue', rec)
  },
  { deep: true },
)
</script>

<template>
  <div class="keyed-group-editor">
    <div v-for="(g, i) in groups" :key="i" class="kge-group">
      <div class="kge-head">
        <el-input v-model="g.key" placeholder="分类名（如 命名 / 测试 / 前端）" class="kge-key" />
        <el-button text type="danger" @click="removeGroup(i)">删除分类</el-button>
      </div>
      <div v-for="(_it, j) in g.items" :key="j" class="kge-item">
        <el-input v-model="g.items[j]" :placeholder="placeholder" />
        <el-button text type="danger" @click="removeItem(g, j)">×</el-button>
      </div>
      <el-button text type="primary" size="small" @click="addItem(g)">+ 添加条目</el-button>
    </div>
    <el-button text type="primary" @click="add">{{ addLabel || '添加分类' }}</el-button>
  </div>
</template>

<style scoped lang="scss">
.keyed-group-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.kge-group {
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.kge-head {
  display: flex;
  gap: 8px;
  align-items: center;
  :deep(.kge-key) {
    max-width: 280px;
  }
}
.kge-item {
  display: flex;
  gap: 8px;
  align-items: center;
  padding-left: 12px;
  :deep(.el-input) {
    flex: 1;
  }
}
</style>
