<script setup lang="ts">
defineProps<{
  title: string
  checkItems: string[]
  nextStage: string
}>()
</script>

<template>
  <div class="confirm-card">
    <div class="card-header">
      <svg class="pause-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2">
        <rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>
      </svg>
      <span class="card-title">{{ title }}</span>
    </div>
    <div class="card-body">
      <ul class="check-list">
        <li v-for="(item, index) in checkItems" :key="index" class="check-item">
          <svg class="check-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
          <span>{{ item }}</span>
        </li>
      </ul>
    </div>
    <div class="card-actions">
      <button class="action-btn action-btn--primary">确认，继续{{ nextStage }}</button>
      <button class="action-btn action-btn--outline">我有修改意见</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.confirm-card {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 14px 16px;
  max-width: 480px;
  margin: 0 auto;
  width: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.pause-icon {
  flex-shrink: 0;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #92400e;
}

.card-body {
  margin-bottom: 14px;
}

.check-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.check-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #451a03;
  padding: 4px 0;

  &:not(:last-child) { border-bottom: 1px dashed #fde68a; }
}

.check-icon {
  color: #f59e0b;
  flex-shrink: 0;
  margin-top: 2px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;

  &--primary {
    background: #f59e0b;
    color: #fff;
    border: none;
    &:hover { background: #d97706; }
  }

  &--outline {
    background: transparent;
    color: #9ca3af;
    border: 1px solid #d1d5db;
    &:hover {
      background: #fff;
      color: #6b7280;
    }
  }
}
</style>
