<script setup lang="ts">
defineProps<{
  actions: Array<{ id: string; label: string; prompt: string; highlighted?: boolean }>
}>()

const emit = defineEmits<{
  (e: 'select', prompt: string): void
}>()
</script>

<template>
  <div class="quick-actions">
    <button
      v-for="action in actions"
      :key="action.id"
      class="quick-actions__btn"
      :class="{ 'quick-actions__btn--highlighted': action.highlighted }"
      :title="action.label"
      @click="emit('select', action.prompt)"
    >
      <span>{{ action.label }}</span>
    </button>
  </div>
</template>

<style scoped lang="scss">
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-actions__btn {
  min-height: 28px;
  padding: 5px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;

  &:hover {
    border-color: #cbd5e1;
    background: #fff;
    color: #334155;
  }
}

.quick-actions__btn--highlighted {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 700;
}
</style>
