<script setup lang="ts">
import { computed, ref } from 'vue'
import { usePipelineStore } from '@/stores/pipeline'
import type {
  Artifact,
  PipelineRun,
  PipelineStageState,
  StageConfirmationAction,
} from '@/types'

const props = defineProps<{
  pipelineRun: PipelineRun
  stage: PipelineStageState
  artifact?: Artifact | null
}>()

const emit = defineEmits<{
  resolved: [action: StageConfirmationAction]
}>()

const pipelineStore = usePipelineStore()
const feedback = ref('')
const error = ref('')
const showRevision = ref(false)
const pendingAction = ref<StageConfirmationAction | null>(null)

const nextStageName = computed(() => {
  const nextStage = [...props.pipelineRun.stages]
    .sort((a, b) => a.order_index - b.order_index)
    .find((item) => item.order_index > props.stage.order_index && item.status !== 'skipped')
  return nextStage?.stage_name ?? '交付完成'
})

const confirmTitle = computed(() => `${props.stage.stage_name}等待确认`)
const artifactName = computed(() => props.artifact?.name ?? '阶段产物已生成')
const isBusy = computed(() => pendingAction.value !== null)

async function submit(action: StageConfirmationAction) {
  if (action === 'revise' && !feedback.value.trim()) {
    error.value = '请先填写修改意见'
    showRevision.value = true
    return
  }

  pendingAction.value = action
  error.value = ''
  try {
    await pipelineStore.confirmStage(
      props.stage.stage_id,
      action,
      action === 'revise' ? feedback.value.trim() : null,
    )
    if (action !== 'revise') {
      feedback.value = ''
    }
    showRevision.value = false
    emit('resolved', action)
  } catch {
    error.value = '操作失败，请稍后重试'
  } finally {
    pendingAction.value = null
  }
}
</script>

<template>
  <div class="confirm-card" data-testid="confirm-card">
    <div class="confirm-card__header">
      <span class="confirm-card__mark" aria-hidden="true">||</span>
      <div class="confirm-card__title-group">
        <span class="confirm-card__title">{{ confirmTitle }}</span>
        <span class="confirm-card__meta">确认后进入：{{ nextStageName }}</span>
      </div>
    </div>

    <div class="confirm-card__body">
      <div class="artifact-row">
        <div class="artifact-row__main">
          <span class="artifact-row__label">待确认产物</span>
          <RouterLink
            v-if="artifact"
            class="artifact-row__link"
            :to="`/artifacts/${artifact.id}`"
          >
            {{ artifactName }}
          </RouterLink>
          <span v-else class="artifact-row__placeholder">{{ artifactName }}</span>
        </div>
        <RouterLink
          v-if="artifact"
          class="artifact-row__action"
          :to="`/artifacts/${artifact.id}`"
        >
          查看产物并交付
        </RouterLink>
      </div>

      <div v-if="showRevision" class="revision-box">
        <textarea
          v-model="feedback"
          class="revision-box__input"
          rows="3"
          placeholder="写下需要补充或重做的点，Agent 会带着这些意见重新执行当前阶段"
          :disabled="isBusy"
        />
        <span v-if="error" class="revision-box__error">{{ error }}</span>
      </div>
      <span v-else-if="error" class="revision-box__error">{{ error }}</span>
    </div>

    <div class="confirm-card__actions">
      <button
        class="action-btn action-btn--primary"
        :disabled="isBusy"
        @click="submit('approve')"
      >
        {{ pendingAction === 'approve' ? '确认中...' : '确认继续' }}
      </button>
      <button
        class="action-btn action-btn--outline"
        :disabled="isBusy"
        @click="showRevision ? submit('revise') : (showRevision = true)"
      >
        {{ showRevision ? (pendingAction === 'revise' ? '提交中...' : '提交修改意见') : '我有修改意见' }}
      </button>
      <button
        class="action-btn action-btn--danger"
        :disabled="isBusy"
        @click="submit('cancel')"
      >
        {{ pendingAction === 'cancel' ? '终止中...' : '终止需求' }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.confirm-card {
  align-self: center;
  width: min(560px, 100%);
  border: 1px solid #f4c669;
  border-radius: 8px;
  background: #fff9e8;
  padding: 14px 16px;
  box-shadow: 0 6px 20px rgba(127, 84, 12, 0.08);
}

.confirm-card__header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.confirm-card__mark {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #f59e0b;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  flex-shrink: 0;
}

.confirm-card__title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.confirm-card__title {
  color: #7c4a03;
  font-size: 14px;
  font-weight: 600;
}

.confirm-card__meta {
  color: #8a6a2a;
  font-size: 12px;
}

.confirm-card__body {
  margin-top: 12px;
}

.artifact-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(244, 198, 105, 0.54);
}

.artifact-row__main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.artifact-row__label {
  color: #8a6a2a;
  font-size: 12px;
  flex-shrink: 0;
}

.artifact-row__link,
.artifact-row__placeholder {
  color: #4b5563;
  font-size: 13px;
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-row__link {
  text-decoration: none;

  &:hover {
    color: #92400e;
    text-decoration: underline;
  }
}

.artifact-row__action {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 9px;
  border-radius: 6px;
  border: 1px solid #d97706;
  color: #92400e;
  background: #fff7df;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;

  &:hover {
    background: #ffefd0;
    border-color: #b45309;
  }
}

.revision-box {
  margin-top: 10px;
}

.revision-box__input {
  width: 100%;
  resize: vertical;
  min-height: 76px;
  max-height: 160px;
  border: 1px solid #e7c46d;
  border-radius: 6px;
  padding: 9px 10px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  line-height: 1.5;
  outline: none;

  &:focus {
    border-color: #f59e0b;
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.16);
  }
}

.revision-box__error {
  display: block;
  margin-top: 6px;
  color: #b91c1c;
  font-size: 12px;
}

.confirm-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.action-btn {
  min-height: 30px;
  border-radius: 6px;
  border: 1px solid transparent;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;

  &:disabled {
    cursor: not-allowed;
    opacity: 0.64;
  }
}

.action-btn--primary {
  color: #fff;
  background: #d97706;

  &:hover:not(:disabled) {
    background: #b45309;
  }
}

.action-btn--outline {
  color: #7c4a03;
  background: #fff;
  border-color: #e7c46d;

  &:hover:not(:disabled) {
    background: #fff7df;
  }
}

.action-btn--danger {
  color: #b91c1c;
  background: transparent;
  border-color: #f3b7b7;

  &:hover:not(:disabled) {
    background: #fff1f1;
  }
}

@media (max-width: 640px) {
  .confirm-card {
    padding: 12px;
  }

  .confirm-card__actions {
    display: grid;
    grid-template-columns: 1fr;
  }

  .artifact-row {
    align-items: stretch;
    flex-direction: column;
  }

  .artifact-row__action {
    justify-content: center;
  }
}
</style>
