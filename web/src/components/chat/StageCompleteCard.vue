<script setup lang="ts">
defineProps<{
  stage: string
  artifactName: string
}>()
</script>

<template>
  <div class="stage-complete-card">
    <div class="card-header">
      <svg class="success-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#67c23a" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><path d="M8 12l3 3 6-6"/>
      </svg>
      <span class="card-title">{{ stage }}完成</span>
    </div>
    <div class="card-body">
      <p class="artifact-info">产物：<span class="artifact-name">{{ artifactName }}</span></p>
    </div>
    <div class="card-actions">
      <button class="action-btn action-btn--secondary">查看</button>
      <button class="action-btn action-btn--primary">确认，进入下一阶段</button>
      <button class="action-btn action-btn--outline">我要修改</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stage-complete-card {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
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
  margin-bottom: 8px;
}

.success-icon {
  flex-shrink: 0;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #166534;
}

.card-body {
  margin-bottom: 12px;
}

.artifact-info {
  font-size: 13px;
  color: #374151;
  margin: 0;
}

.artifact-name {
  font-weight: 500;
  color: #166534;
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

  &--secondary {
    background: #fff;
    color: #6b7280;
    border: 1px solid #d1d5db;
    &:hover { background: #f9fafb; }
  }

  &--primary {
    background: #67c23a;
    color: #fff;
    border: none;
    &:hover { background: #52c41a; }
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
