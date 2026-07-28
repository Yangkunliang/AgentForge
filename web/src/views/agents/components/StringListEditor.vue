<script setup lang="ts">
import { reactive, onMounted, watch } from 'vue'

const props = defineProps<{
  modelValue: string[]
  placeholder?: string
  addLabel?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string[]): void }>()

const items = reactive<string[]>([])

onMounted(() => {
  items.splice(0, items.length, ...(props.modelValue ? [...props.modelValue] : []))
})

function add() {
  items.push('')
}
function remove(i: number) {
  items.splice(i, 1)
}

// 任意改动都向上 emit（丢弃空白草稿）
watch(
  items,
  () => {
    emit(
      'update:modelValue',
      items.filter((x) => x.trim() !== ''),
    )
  },
  { deep: true },
)
</script>

<template>
  <div class="string-list-editor">
    <div v-for="(_item, i) in items" :key="i" class="sli-row">
      <el-input v-model="items[i]" :placeholder="placeholder" />
      <el-button text type="danger" @click="remove(i)">删除</el-button>
    </div>
    <el-button text type="primary" @click="add">{{ addLabel || '添加一项' }}</el-button>
  </div>
</template>

<style scoped lang="scss">
.string-list-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sli-row {
  display: flex;
  gap: 8px;
  align-items: center;
  :deep(.el-input) {
    flex: 1;
  }
}
</style>
