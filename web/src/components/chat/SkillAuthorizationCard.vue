<script setup lang="ts">
import { computed } from 'vue'
import { Close, Unlock } from '@element-plus/icons-vue'
import type { SkillAuthorizationRequest } from '@/types'

const props = defineProps<{
  request: SkillAuthorizationRequest
  busy?: boolean
}>()

const emit = defineEmits<{
  authorize: []
  dismiss: []
}>()

const permissions = computed(() => {
  const values = props.request.skills.flatMap((skill) => skill.permissions)
  return [...new Set(values)].filter(Boolean)
})
</script>

<template>
  <div class="skill-auth-card" data-testid="skill-authorization-card">
    <div class="skill-auth-card__header">
      <span class="skill-auth-card__icon" aria-hidden="true">
        <el-icon><Unlock /></el-icon>
      </span>
      <div class="skill-auth-card__title-group">
        <span class="skill-auth-card__title">需要授权高风险 Skill</span>
        <span class="skill-auth-card__meta">
          本阶段请求使用 {{ request.skills.length }} 个受限工具
        </span>
      </div>
      <button class="skill-auth-card__close" title="忽略" @click="emit('dismiss')">
        <el-icon><Close /></el-icon>
      </button>
    </div>

    <div class="skill-auth-card__body">
      <div class="skill-auth-card__skills">
        <span
          v-for="skill in request.skills"
          :key="`${skill.skill_name}:${skill.tool_name}`"
          class="skill-auth-card__skill"
          :title="skill.tool_name"
        >
          {{ skill.skill_name }}
        </span>
      </div>
      <div v-if="permissions.length" class="skill-auth-card__permissions">
        <span
          v-for="permission in permissions"
          :key="permission"
          class="skill-auth-card__permission"
        >
          {{ permission }}
        </span>
      </div>
    </div>

    <div class="skill-auth-card__actions">
      <button
        class="skill-auth-card__btn skill-auth-card__btn--primary"
        :disabled="busy"
        @click="emit('authorize')"
      >
        {{ busy ? '重试中...' : '授权本阶段并重试' }}
      </button>
      <button
        class="skill-auth-card__btn skill-auth-card__btn--ghost"
        :disabled="busy"
        @click="emit('dismiss')"
      >
        忽略
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.skill-auth-card {
  align-self: center;
  width: min(560px, 100%);
  border: 1px solid #f7b4a5;
  border-radius: 8px;
  background: #fff6f3;
  padding: 14px 16px;
  box-shadow: 0 6px 20px rgba(146, 64, 14, 0.08);
}

.skill-auth-card__header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.skill-auth-card__icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #f97316;
  color: #fff;
  flex-shrink: 0;
}

.skill-auth-card__title-group {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.skill-auth-card__title {
  color: #9a3412;
  font-size: 14px;
  font-weight: 600;
}

.skill-auth-card__meta {
  color: #9f5a2c;
  font-size: 12px;
}

.skill-auth-card__close {
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 6px;
  color: #a16207;
  background: transparent;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: rgba(249, 115, 22, 0.12);
    color: #7c2d12;
  }
}

.skill-auth-card__body {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skill-auth-card__skills,
.skill-auth-card__permissions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-auth-card__skill,
.skill-auth-card__permission {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  border-radius: 6px;
  padding: 3px 8px;
  font-size: 12px;
  line-height: 1.2;
}

.skill-auth-card__skill {
  background: #fff;
  border: 1px solid rgba(249, 115, 22, 0.24);
  color: #7c2d12;
  font-weight: 600;
}

.skill-auth-card__permission {
  background: rgba(249, 115, 22, 0.1);
  color: #9a3412;
}

.skill-auth-card__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.skill-auth-card__btn {
  height: 32px;
  border-radius: 6px;
  padding: 0 12px;
  border: 1px solid transparent;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.skill-auth-card__btn--primary {
  background: #f97316;
  color: #fff;

  &:hover:not(:disabled) {
    background: #ea580c;
  }
}

.skill-auth-card__btn--ghost {
  background: transparent;
  color: #9a3412;
  border-color: rgba(249, 115, 22, 0.3);

  &:hover:not(:disabled) {
    background: rgba(249, 115, 22, 0.1);
  }
}
</style>
